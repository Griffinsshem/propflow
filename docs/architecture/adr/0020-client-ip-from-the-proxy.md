# ADR 0020: The visitor's IP comes from the frontend proxy, not from counting hops

## Status
Accepted. Found by the live check on the free deployment (ADR 0019).

## Context
Rate limits, sessions and the audit log key on the client IP. The API found it by counting
`TRUSTED_PROXY_COUNT` entries back in `X-Forwarded-For` (ProxyFix). On the live deployment every
recorded IP was a Cloudflare edge address (172.64.0.0/13): Render's edge adds hops we do not
control, so any fixed count is fragile.

## Decision
- The frontend proxy, which already authenticates with `PROXY_SHARED_SECRET`, sends the visitor's
  IP (from Vercel's platform-set `x-forwarded-for`) in `X-PropFlow-Client-IP`. Browser-supplied
  copies are never forwarded (the proxy forwards an allowlist).
- `app/common/client_ip.py`, the innermost WSGI middleware, sets `REMOTE_ADDR` from that header
  only when the secret matches (constant-time comparison) and the value is one valid IP. The
  header is removed from every request.
- `TRUSTED_PROXY_COUNT` stays set in production, which keeps the proxy secret mandatory.

## Consequences
- Rate limits, sessions and audit entries record the real visitor, whatever the hop count.
- Requests without the secret are refused anyway; their IP is never trusted from a header.
- Verification without Render's Shell (free plan): sign in on the live site, then read the newest
  `user_sessions.ip_address` from the Neon database and compare it with your public IP.
