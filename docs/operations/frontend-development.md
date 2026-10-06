# Frontend development

| Task | Command (in `frontend/`) |
|---|---|
| Run against the local API | API: `flask run --port 5000` (in `backend/`); then `npm run dev` |
| Lint, types, unit tests | `npm run lint && npm run typecheck && npm run test` |
| End-to-end tests | API: `EMAIL_BACKEND=file EMAIL_FILE_DIR=/tmp/propflow-mail TRUSTED_PROXY_COUNT=1 flask run --port 5000`; then `redis-cli -n 2 flushdb && npm run build && E2E_MAIL_DIR=/tmp/propflow-mail npx playwright test` |

Server-only settings (in `frontend/.env.local`, never `NEXT_PUBLIC_`):

| Variable | Default | Purpose |
|---|---|---|
| `API_ORIGIN` | `http://127.0.0.1:5000` | where the proxy forwards `/api/v1/*` |
| `PROXY_SHARED_SECRET` | unset | must equal the API's value when the API enforces it |

End-to-end runs register uniquely named `e2e-…@example.com` accounts. Registration is limited
to 20 per hour per IP; clear local counters with `redis-cli -n 2 flushdb` if needed.

## Conventions

- **Organization-scoped cache keys** start with `["org", organizationId, ...]`. Switching
  organizations removes every non-`auth` query before refetching, so data from two
  organizations can never mix on screen.
- **Navigation** (`src/features/navigation/nav.ts`) lists a section only once its page
  exists, filtered by the active role. It is convenience, not security: the API authorizes
  every request.
- **End-to-end helpers** live in `e2e/support.ts`.
- **Concurrent edits** (`src/lib/conflict.ts`): saves send only changed fields plus the
  version they started from. A `409` whose record version moved shows the other person's
  changes; "Keep my changes" keeps only the fields this user edited and takes theirs for the
  rest, so a save never silently reverts someone else's work. A `409` without a version change
  (for example a duplicate label) is an ordinary error.
- **End-to-end visitors** (`e2e/fixtures.ts`): each test sends its own `X-Forwarded-For` from
  the reserved `198.18.0.0/15` range, so per-IP rate limits apply per simulated person. Specs
  import `test` and `expect` from `./fixtures`, not from `@playwright/test`.
