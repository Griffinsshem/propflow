# Frontend development

| Task | Command (in `frontend/`) |
|---|---|
| Run against the local API | API: `flask run --port 5000` (in `backend/`); then `npm run dev` |
| Lint, types, unit tests | `npm run lint && npm run typecheck && npm run test` |
| End-to-end tests | API running, then `npm run build && npx playwright test` |

Server-only settings (in `frontend/.env.local`, never `NEXT_PUBLIC_`):

| Variable | Default | Purpose |
|---|---|---|
| `API_ORIGIN` | `http://127.0.0.1:5000` | where the proxy forwards `/api/v1/*` |
| `PROXY_SHARED_SECRET` | unset | must equal the API's value when the API enforces it |

End-to-end runs register uniquely named `e2e-…@example.com` accounts. Registration is limited
to 20 per hour per IP; clear local counters with `redis-cli -n 2 flushdb` if needed.
