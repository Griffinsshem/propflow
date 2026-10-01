# PropFlow

A secure, multi-tenant property operations platform that centralizes maintenance
workflows between tenants, property managers and contractors.

**Status:** Phase 0, repository and toolchain initialized. Not production-ready.

**Deployment target:** Vercel (frontend) and Render (API, worker, Postgres, Key Value).
See `docs/architecture/adr/0001-deployment-platform.md`.

## Local development (Ubuntu)
1. Install PostgreSQL and Redis: `sudo apt-get install -y postgresql redis-server`
2. Create the `propflow` role and the `propflow` and `propflow_test` databases, then `cp .env.example .env` and fill in values
3. Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt`
4. Frontend: `cd frontend && npm install && npm run dev`
