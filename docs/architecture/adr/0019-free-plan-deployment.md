# ADR 0019: A zero-cost first deployment

## Status
Accepted. The paid production design (render.yaml, ADR 0014) remains the target.

## Context
The first deployment must cost nothing. Render's free plan has no background workers and no
pre-deploy step, its free Postgres expires after 30 days, and since September 2025 its free web
services cannot reach SMTP ports 25, 465 or 587.

## Decision
- `render.free.yaml`: a free API web service and a free Key Value store, in Frankfurt.
- No Celery worker or scheduler: `BACKGROUND_TASKS=sync` (production config accepts it), so
  email and photo processing run inside the request; `GUNICORN_TIMEOUT=60` covers photo
  processing on 0.1 CPU. Housekeeping jobs (expired sessions, abandoned uploads, old
  notifications) do not run.
- Database on Neon's free plan (Frankfurt, Postgres 16, direct connection, TLS required).
  Migrations run at the end of the build, since free instances have no pre-deploy step.
- Email through Brevo's free plan over SMTP port 2525 with STARTTLS. Without a verified domain,
  Brevo sends from its own `brevosend.com` address.
- Key Value holds only rate-limit counters, so `allkeys-lru` replaces `noeviction`.
- Frontend on Vercel Hobby; photos on Cloudflare R2's free allowance.

## Consequences
- The API sleeps after 15 minutes idle; the first request afterwards is slow.
- Requests that send email or process a photo are slower than with a worker.
- Housekeeping does not run; acceptable at small scale, required before real growth.
- Moving to render.yaml later is configuration: a worker, a scheduler, a paid API, and either
  Neon or Render Postgres.
