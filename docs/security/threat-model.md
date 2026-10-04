# PropFlow threat model

Security is continuous risk reduction, not a finished state. This document maps the threats
in spec section 78 to their mitigations, the automated tests that prove them, and the risk
that remains. It is reviewed whenever a feature changes a trust boundary.

## Assets
Tenant personal data (names, emails, phones, unit placement), maintenance photos (may show
home interiors), credentials and sessions, organization operational data, audit history.

## Trust boundaries
```text
Browser ──HTTPS──► Vercel (Next.js, adds X-Proxy-Secret) ──HTTPS──► Flask API (Render)
                                                                    │
                                     ┌──────────────┬───────────────┼──────────────┐
                                     ▼              ▼               ▼              ▼
                                 PostgreSQL       Redis      Celery worker   Cloudflare R2
                                 (private)     (private)                   (private bucket)
Browser ──presigned URL (5 min)──────────────────────────────────────────────► Cloudflare R2
```

## Adversaries
Anonymous internet users; authenticated users of another organization; lower-privileged
members of the same organization (tenant, contractor); a stolen session; someone calling
the API origin directly; a compromised dependency.

## Authentication
| Threat | Mitigation | Evidence | Residual risk |
|---|---|---|---|
| Brute force, credential stuffing | Per-IP and per-account login limits (failures only), Argon2id | `security/test_rate_limits.py` | No MFA yet; no breached-password check |
| Account enumeration | Identical login errors and timing; identical forgot-password response | `integration/test_auth.py`, `test_account_recovery.py` | Registration reveals existing emails (ADR 0003) |
| Stolen session | HttpOnly `__Host-` cookie, server-side revocation, idle and absolute expiry | `integration/test_auth.py` | No device list or suspicious-login alerts yet |
| Session fixation | New token on every login; previous session revoked | `integration/test_auth.py` | - |
| Password-reset abuse | Signed 30-minute single-use links, per-account limit, all sessions revoked on reset | `integration/test_account_recovery.py` | Email account compromise = account compromise |
| CSRF | Origin check plus session-bound HMAC CSRF token; SameSite=Lax | `integration/test_auth.py` (CSRF tests) | - |

## Authorization
| Threat | Mitigation | Evidence | Residual risk |
|---|---|---|---|
| Cross-tenant access (IDOR/BOLA) | Org context from server session; org-scoped queries; 404 for foreign IDs; composite foreign keys | `security/test_cross_tenant*.py`, `integration/test_*_integrity.py` | Application-level scoping (RLS deferred, ADR 0005) |
| Horizontal escalation (tenant to neighbour, contractor to contractor) | Per-role visibility rules in repositories | `test_maintenance.py`, `test_work_orders.py`, `test_attachments.py` | - |
| Vertical escalation (tenant to manager) | Central permission matrix; role changes owner-only; last-owner lock | `unit/test_permissions.py`, `test_members.py`, `test_policies.py` | - |
| Mass assignment | Schemas reject unknown fields; server-controlled fields never accepted | `test_auth.py`, `test_properties.py`, `test_organizations.py` | - |
| Leaked invitation link | Bound to the invited email; single-use; expiring | `integration/test_invitations.py` | - |

## Application
| Threat | Mitigation | Evidence | Residual risk |
|---|---|---|---|
| SQL injection | SQLAlchemy parameterized queries only; the one raw statement uses no input | bandit in CI | - |
| XSS (stored, reflected, DOM) | Plain text stored verbatim; JSON only; `nosniff`; API CSP `default-src 'none'`; React escapes output | `test_maintenance.py` (markup round-trip), `security/test_hardening.py` | Frontend CSP pending (frontend phase) |
| Malicious uploads | Decoded by Pillow, format must match, size and pixel bounds, re-encoded (strips EXIF/GPS and polyglot payloads), server-generated keys | `integration/test_attachments.py` | Images only; documents (V2) will need malware scanning |
| Path traversal | Storage keys built only from server UUIDs | `test_attachments.py` | - |
| SSRF, command injection | The API never fetches user-supplied URLs or runs shell commands | code review | Re-assess if webhooks or imports are added |
| Log injection | Client request IDs validated; query strings never logged | `test_app_foundation.py` | - |

## Infrastructure
| Threat | Mitigation | Evidence | Residual risk |
|---|---|---|---|
| Exposed secrets | `.env` git-ignored; config refuses weak or placeholder secrets; gitleaks on full history | `unit/test_config.py`, CI secret scan | Manual rotation process (incident docs, Phase 13) |
| Vulnerable dependencies | pip-audit and npm audit in CI; Dependabot PRs gated by CI | CI | Zero-days before advisories exist |
| Direct origin access (IP spoofing) | Proxy shared secret required on `/api`; production refuses proxy trust without it | `security/test_hardening.py`, `unit/test_config.py` | Secret must be rotated if leaked |
| CORS misconfiguration | No CORS at all: the browser only talks to the same origin through the proxy | ADR 0001 | - |
| Exposed database or broker | Render private networking; broker holds only short-lived jobs | deployment docs (Phase 13) | Broker contents include email links (ADR 0011) |
| Public storage | Private bucket; 5-minute presigned URLs issued only after authorization | `test_attachments.py` | URL valid for 5 minutes if forwarded |

## Availability
| Threat | Mitigation | Evidence | Residual risk |
|---|---|---|---|
| Request flooding | Redis-backed limits per user or IP; per-endpoint limits | `security/test_rate_limits.py` | Volumetric DDoS needs edge protection (Vercel/Cloudflare) |
| Expensive queries | Pagination caps (100); indexed keyset pagination; dashboard query-count test | `test_audit_log.py`, `test_dashboards.py` | Load-test evidence: Phase 11b |
| Oversized payloads | 1 MB API body limit; uploads bypass the API; 10 MB image cap | `test_app_foundation.py`, `test_attachments.py` | - |
| Upload abuse | Upload rate limits; 10 per request; abandoned uploads cleaned up | `test_attachments.py`, `test_housekeeping.py` | - |
| Redis or worker outage | Rate limiting falls back to memory; enqueue failures logged; housekeeping re-queues stuck jobs | `test_email_delivery.py`, `test_housekeeping.py` | Emails during an outage need a user retry |

## Known gaps (tracked, not hidden)
MFA and elevated-action confirmation for owners; suspicious-login detection; tamper-evident
audit storage outside the database; row-level security; malware scanning for future document
uploads; platform-administrator tooling; frontend CSP. Each is a roadmap item, not a claim.
