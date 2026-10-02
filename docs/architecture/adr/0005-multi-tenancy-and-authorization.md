# ADR 0005: Multi-tenancy and authorization

## Status
Accepted

## Decision
Every organization-scoped request passes three independent checks:

1. **Organization context** comes from the server-side session's active organization,
   never from request input. Membership (and organization status) is re-verified on every
   request, so removal or suspension takes effect immediately.
2. **Role permission**: a central, immutable role-to-permission matrix
   (`app/authz/permissions.py`) enforced by `@require_permission`. No `if role == ...`
   checks scattered through the code.
3. **Object scope**: repositories filter by `organization_id` (and, per feature, by
   tenant/assignment). Out-of-scope records return 404, identical to nonexistent ones,
   so other organizations' resource IDs cannot be confirmed.

Permission matrix (MVP spec 3.1): owner has everything; manager has everything except
organization settings, member management, audit log, and property create/update/delete
(managers view assigned properties); tenant can read their org/unit and create, read and
comment on maintenance; contractor can read/update work orders and comment.

## Audit log
- Written inside the same transaction as the change it describes.
- Append-only enforced by a Postgres trigger; DELETE is allowed only with a
  transaction-local maintenance flag (test teardown, future retention jobs).
- Detail keys resembling secrets are dropped before storage.
- Limit: protects against application bugs, not a database owner. Tamper-evident
  external storage is a later hardening option.

## Alternatives considered
- **Organization ID in URLs** (`/orgs/{id}/properties`): explicit, but invites trusting
  client-supplied IDs. Rejected in favor of session context.
- **Postgres row-level security**: strong defense in depth, but requires per-transaction
  session variables that interact poorly with pooled connections. Deferred; the mandatory
  cross-tenant test suite guards the application-level scoping in the meantime.
