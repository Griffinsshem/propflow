# ADR 0001: Deploy to Vercel (frontend) and Render (backend), no Docker for now

## Status
Accepted

## Problem
The project spec calls for Docker-based deployment. The chosen hosting platforms
build directly from the repository, and local Docker adds setup cost without
deployment benefit at this stage.

## Decision
- Frontend: Next.js on Vercel.
- Backend: Flask (gunicorn) as a Render Web Service; Celery as a Render Background Worker.
- Data: Render Postgres and Render Key Value (Redis-compatible).
- Local development: native PostgreSQL and Redis. CI uses ephemeral service containers.
- The browser talks only to the frontend origin; Next.js rewrites `/api/v1/*` to the
  backend, so the session cookie stays first-party (`SameSite=Lax`).

## Alternatives considered
- Docker Compose locally plus container deploys: more portable, but unnecessary for these platforms today.
- Calling the API cross-site directly: needs `SameSite=None` cookies, which browsers increasingly block.

## Trade-offs
- An extra proxy hop on API calls. Uploads use presigned URLs so large bodies skip the proxy.
- Rate limiting must derive the client IP from trusted proxy headers.
- Free-tier services may sleep when idle (cold starts) and have limits; check current Render plans.
- Docker remains an option later (Render also supports Dockerfile deploys) if portability becomes a need.
