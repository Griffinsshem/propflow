#!/usr/bin/env bash
# Runs PropFlow locally the way production runs it: gunicorn API, Celery worker and scheduler
# (the commands from render.yaml), and a production build of the frontend. Ctrl+C stops all.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIL_DIR=/tmp/propflow-mail
STORAGE_DIR=/tmp/propflow-storage

fail() { echo "✗ $*" >&2; exit 1; }
[ -f "$ROOT/.env" ] || fail "No .env at the repository root: create it from .env.example first."
[ -x "$ROOT/backend/.venv/bin/python" ] || fail "backend/.venv not found."
pg_isready -q || fail "PostgreSQL is not running (sudo systemctl start postgresql)."
[ "$(redis-cli ping 2>/dev/null)" = "PONG" ] || fail "Redis is not running (sudo systemctl start redis-server)."
for port in 5000 3000; do
  if ss -ltn "sport = :$port" | grep -q LISTEN; then
    fail "Port $port is in use: stop what runs there first (an earlier 'flask run' or 'npm start')."
  fi
done

# Environment wins over .env (config.py loads it with override=False): local stand-ins for
# email and storage, and real background tasks through Celery, as in production.
export APP_ENV=development EMAIL_BACKEND=file EMAIL_FILE_DIR="$MAIL_DIR" \
  STORAGE_BACKEND=local LOCAL_STORAGE_DIR="$STORAGE_DIR" BACKGROUND_TASKS=async TRUSTED_PROXY_COUNT=1
mkdir -p "$MAIL_DIR" "$STORAGE_DIR"

cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
python -c 'from app.config import build_config; build_config("development")' \
  || fail "Configuration is incomplete: the message above names the missing setting."
flask db upgrade
# The frontend must present the proxy secret the API expects, if one is configured.
secret="$(python -c 'from dotenv import dotenv_values; print(dotenv_values("../.env").get("PROXY_SHARED_SECRET") or "")')"
if [ -n "$secret" ]; then export PROXY_SHARED_SECRET="$secret"; fi

echo "Building the frontend (a production build, as deployed)…"
(cd "$ROOT/frontend" && npm run build >/dev/null) || fail "Frontend build failed: run 'npm run build' in frontend/ to see why."

run() { local name=$1; shift; ( "$@" 2>&1 | sed -u "s/^/[$name] /" ) & }
stop() { trap - INT TERM EXIT; echo; echo "Stopping PropFlow…"; kill 0 2>/dev/null || true; }
trap stop INT TERM EXIT

run api gunicorn -c gunicorn.conf.py wsgi:app --bind 127.0.0.1:5000 --workers 2
run worker celery -A celery_worker.celery worker --loglevel=INFO --concurrency=1 --max-tasks-per-child=200
run beat celery -A celery_worker.celery beat --loglevel=INFO --schedule=/tmp/propflow-celerybeat-schedule
run web bash -c "cd '$ROOT/frontend' && exec npm run start"

for _ in $(seq 1 60); do curl -fs -o /dev/null http://localhost:3000/login && break; sleep 1; done
echo
echo "PropFlow is running at http://localhost:3000"
echo "  Demo data:  cd backend && source .venv/bin/activate && python scripts/seed_demo.py"
echo "  Emails:     python3 scripts/mailbox.py"
echo "  Stop:       Ctrl+C"
wait
