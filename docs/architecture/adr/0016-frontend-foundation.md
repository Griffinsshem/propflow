# ADR 0016: Frontend foundation

## Status
Accepted

## Decisions
- **API proxy as a route handler** (`src/app/api/v1/[...path]/route.ts`), not a rewrite: it
  adds the proxy secret server-side, forwards an allowlist of request headers (dropping any
  client-supplied `x-proxy-secret` or `x-forwarded-for`), sets exactly one
  `X-Forwarded-For` value (the client IP reported by the platform), refuses path traversal,
  preserves every `Set-Cookie`, and returns the API's error envelope on upstream failure.
- **Nonce-based CSP** per request (`src/proxy.ts`): scripts need the nonce
  (`'strict-dynamic'`); inline styles are allowed because Next's route announcer uses them and
  style injection is far lower risk than script injection. The root layout renders per request
  so every page carries its nonce. Static headers live in `next.config.ts`.
- **CSRF:** the client echoes the readable CSRF cookie (`__Host-` in production, plain in
  development) in `X-CSRF-Token` on unsafe methods.
- **Route guard is UX only:** the API authorizes every request; the signed-in layout only
  redirects signed-out visitors (with a validated, same-site `next` path).
- **Shared devices:** sign-out clears the entire client cache.
- **Tests:** Vitest for pure rules and components; Playwright end-to-end against the real API,
  which enforces the proxy secret in CI, so the proxy path is proven in every run.
