# ADR 0004: Rate limiting and account recovery

## Status
Accepted

## Rate limiting
- Flask-Limiter with Redis storage (shared across API instances), sliding-window-counter.
- Default 1000/min keyed by user when authenticated, else IP: Kenyan mobile carriers use
  CGNAT, so many legitimate users can share one IP.
- Login: 20/min and 200/hour per IP; 10 failed attempts per 15 min per target account
  (successful logins don't count). Forgot-password: 3/hour per target account (prevents
  inbox flooding). Register, reset and verify are limited per IP.
- Account keys are SHA-256 hashes of the email; Redis never stores addresses.
- Redis failure: errors are swallowed and limits fall back to per-process memory, so an
  outage degrades protection rather than blocking all logins.
- Client IP: `TRUSTED_PROXY_COUNT` hops (Vercel + Render) via ProxyFix, default 0 until
  verified against real production headers.

## Account recovery
- Stateless itsdangerous tokens signed with SECRET_KEY, purpose-specific salts.
- Password reset: 30-minute expiry, bound to a fingerprint of the current password hash,
  so it is single-use without storage. A reset revokes all sessions.
- Email verification: 48-hour expiry, bound to the email address it was sent to.
- Links carry tokens in the URL fragment (`#token=`), never the query string.
- Forgot-password responds identically whether or not the account exists.

## Known risks
- Requests sent directly to the Render origin (bypassing Vercel) can spoof X-Forwarded-For,
  weakening IP-keyed limits. Account-keyed limits are unaffected. Mitigation at deployment:
  a proxy-secret header added by the frontend and required by the API.
- Rotating SECRET_KEY invalidates all outstanding email links and CSRF tokens (acceptable).
- Email is sent inline for now (console/memory/disabled backends are instant); real
  provider delivery moves to the background worker in Phase 9.
