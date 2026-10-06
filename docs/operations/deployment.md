# Deployment runbook

Infrastructure is defined in `render.yaml` (Render Blueprint); the decisions are in ADR 0014
and the sizing evidence in `docs/performance/load-test-results.md`.

## What runs where

| Component | Render resource | Plan | Notes |
|---|---|---|---|
| API | web `propflow-api` | `1c-2g`, 2 sync workers | `gunicorn.conf.py`; migrations in pre-deploy |
| Background jobs | worker `propflow-worker` | `0.5c-512mb`, concurrency 1 | email, photo processing |
| Scheduler | worker `propflow-beat` | `0.5c-512mb`, **exactly 1 instance** | housekeeping jobs |
| Queue, rate limits | Key Value `propflow-redis` | `256mb`, `noeviction` | private network only |
| Database | Postgres `propflow-db` | `0.5c-1g`, PostgreSQL 16 | private network only |
| Photos | Cloudflare R2 bucket | n/a | private; presigned URLs only |
| Frontend | Vercel (frontend phases) | n/a | the only public entry to `/api` |

All Render resources are in `frankfurt`. Deploy the Vercel functions in the nearest region
(`fra1`) so the proxy hop stays short. Check current plan prices on Render's pricing page
before creating the Blueprint: creating it starts billing.

## Before the first deploy

1. **Cloudflare R2:** create a private bucket; create an API token with *Object Read & Write*
   scoped to that bucket only. Note the S3 endpoint (`https://<account-id>.r2.cloudflarestorage.com`).
2. **R2 CORS** (browsers upload photos directly with presigned PUT URLs):
```json
   [{"AllowedOrigins": ["https://<frontend-domain>"], "AllowedMethods": ["PUT"],
     "AllowedHeaders": ["content-type"], "MaxAgeSeconds": 3600}]
```
   If a browser preflight is rejected, compare the requested headers with this list.
3. **Frontend origin:** the production frontend URL (`https://...`, no trailing slash). If the
   frontend is not deployed yet, use its planned URL and update it later.
4. **Email provider** (any SMTP provider; ADR 0015): create SMTP credentials and verify the
   sending domain by adding the provider's SPF, DKIM and DMARC DNS records. Without them,
   password resets land in spam or are rejected. `MAIL_FROM` must use the verified domain,
   for example `PropFlow <no-reply@yourdomain>`. For a backend-only trial deploy before
   this is ready, set `EMAIL_BACKEND=disabled` in the `propflow-shared` group.

## First deploy

1. Render Dashboard → New → Blueprint → select the repository. Render reads `render.yaml`.
2. Fill in the prompted values on `propflow-api`: `FRONTEND_ORIGIN`, `S3_ENDPOINT_URL`,
   `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `SMTP_HOST`, `SMTP_USERNAME`,
   `SMTP_PASSWORD`, `MAIL_FROM`. The worker and beat reference these.
   If the worker or beat reports a missing S3 variable after the first sync, run a manual
   Blueprint sync once the API exists.
3. Create. Render provisions Postgres and Key Value, builds the three services, runs
   `flask db upgrade` before the API starts, then health-checks `/health`.

## Verify (backend only, before the frontend exists)

| Check | How | Expected |
|---|---|---|
| Python version | API build log | `Using Python version: 3.12.x` |
| Migrations | API deploy log (pre-deploy) | `Running upgrade ... -> <head>` lines, no errors |
| Liveness | `curl https://<api>.onrender.com/health` | `{"status": "ok"}` |
| Dependencies | `curl https://<api>.onrender.com/ready` | database and redis `ok` |
| Proxy secret | `curl -i https://<api>.onrender.com/api/v1/auth/me` | `403`: direct calls are refused |
| Worker | worker logs | `celery@... ready.` |
| Scheduler | beat logs | `beat: Starting...`, then scheduled tasks every 15 minutes |
| Email | request a password reset for a test account | delivered to the inbox (not spam); worker log `email_sent` |

## Verify (after the frontend is deployed)

1. Set `PROXY_SHARED_SECRET` in Vercel (server-only) to the value Render generated in the
   `propflow-shared` group. Set `STORAGE_ORIGIN` (server-only) to the R2 endpoint origin,
   the same host as `S3_ENDPOINT_URL`: the CSP allows exactly that origin for photo uploads
   and display. Then upload a real photo to a request and confirm it shows as ready.
2. **Proxy hop count:** log in through the frontend, then in the Render shell for the API:
   `flask shell` → read the newest `UserSession.ip_address`. It must equal your public IP
   (`curl ifconfig.me`). If it shows a Vercel or Render address, adjust
   `TRUSTED_PROXY_COUNT` and redeploy. A wrong value makes all users share one rate-limit
   bucket.
3. Run the k6 smoke profile against the deployed frontend URL, then the stress profile
   against a staging copy (never production data), and record the results.

## Routine deploys

- Merges to `main` deploy automatically **only after CI passes** (`checksPass`).
- Migrations run before the new version takes traffic while the old version still serves,
  so schema changes must be **backward compatible** (expand → deploy → contract): add
  columns as nullable or with defaults, backfill, switch the code, drop the old columns in a
  later release.

## Rollback

- Code: Render Dashboard → service → Rollback to the previous deploy.
- Schema: migrations are **not** reverted automatically. Because migrations are backward
  compatible (above), the previous code runs against the new schema; roll forward with a fix
  rather than running `flask db downgrade` against production data.

## Secret rotation

| Secret | Procedure | User impact |
|---|---|---|
| `SECRET_KEY` | new value (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) in `propflow-shared`; redeploy all three services | CSRF tokens and outstanding email links become invalid; users sign in again |
| `PROXY_SHARED_SECRET` | update Render, then Vercel immediately, redeploy both | `403`s between the two updates (a dual-secret window is a future improvement) |
| R2 token | create a new token, update the API variables, redeploy, delete the old token | none |
| Database password | rotate in Render; services pick it up via `fromDatabase` on redeploy | brief reconnects |

## Capacity and scaling

- Measured on a 4-core laptop: 8 sync workers reached a knee at 148-177 req/s; 4 workers at
  78-113 req/s. Production numbers must be measured on the deployed stack.
- Keep each instance below ~70% of its measured knee. Scale **out** (more instances) beyond
  that: the API is stateless (sessions in Postgres, limits in Redis).
- Workers per instance: 2 x vCPU (`WEB_CONCURRENCY`), changed together with the plan.
- **Connection budget:** API instances x workers x 2 + worker processes x 2 + beat. Launch:
  1 x 2 x 2 + about 4 + 2 ≈ 10 of the plan's 100 connections.

## Monitoring and alerts

Overload showed up as **queueing delay with zero errors**, so alert on latency and CPU, not
only on error rates:

- API p95 response time above 300 ms for 5 minutes.
- API CPU above 70% sustained (near the knee); memory above 80%.
- Any failed deploy (Render notifications).
- An external uptime check on `/ready` every minute.
- Worker: queue growth or repeated task retries in the logs.

## Launch blockers (production is not ready for real users until these are done)

1. **Email provider configured.** The SMTP backend exists (ADR 0015); production needs real
   credentials and a verified sending domain (SPF, DKIM, DMARC), confirmed by the
   password-reset check above.
2. **Frontend** deployed on Vercel with the proxy secret, and the hop-count verification above.
3. **Database backups** confirmed on the chosen Postgres plan, with a test restore.
4. **Custom domain** and HTTPS for the frontend.
