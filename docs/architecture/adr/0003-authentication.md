# ADR 0003: Authentication with opaque server-side sessions

## Status
Accepted

## Decision
- Opaque 256-bit session tokens in HttpOnly, SameSite=Lax cookies; only a SHA-256 hash is
  stored (`user_sessions`). Production cookie names use the `__Host-` prefix.
- Lifetimes: 3-day idle, 14-day absolute (configurable). `last_seen_at` is written at most
  every 5 minutes.
- CSRF: unsafe API requests with a foreign `Origin` are rejected; authenticated unsafe
  requests must send `X-CSRF-Token = HMAC(SECRET_KEY, session_token_hash)`, delivered in a
  readable cookie. Nothing extra is stored and the token cannot be forged via cookie injection.
- Passwords: Argon2id (argon2-cffi defaults; cheap parameters only in tests), 12-128
  characters, transparent rehash when parameters change.
- Login failures return one generic message; unknown emails still perform a hash
  verification so timing does not reveal account existence.
- Login always issues a new token and revokes the browser's previous session.

## Alternatives considered
- JWT access/refresh tokens: stateless, but revocation needs a denylist anyway and tokens
  are often mishandled in browser storage. Rejected for a browser-first product.
- Flask's signed-cookie session: cannot be revoked server-side. Rejected.

## Trade-offs and known risks
- One indexed lookup per authenticated request (cheap; cacheable in Redis later if measured).
- Registration reveals whether an email is already registered. Mitigated by rate limiting
  (Phase 3b); a verify-email-first flow would remove it and is a candidate for later.
- Argon2 default memory cost (~64 MiB per hash) bounds concurrent logins per instance on
  small Render plans; login rate limiting also protects memory.
