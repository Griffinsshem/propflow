# ADR 0002: Data model conventions

## Status
Accepted

## Decisions
- **UUID primary keys** (uuid4, `gen_random_uuid()` server fallback): IDs in URLs are not
  enumerable. Trade-off: weaker index locality than sequential keys; acceptable at our scale.
- **VARCHAR + named CHECK constraints instead of native Postgres enums**: same integrity,
  far simpler migrations when values are added.
- **Fixed roles in code (owner, manager, tenant, contractor); no Role table**: the spec's
  `Role` entity is deferred until custom roles exist. One role per user per organization.
- **Foreign keys default to RESTRICT**: business records are never removed by cascade.
  Exception: `user_sessions` cascade with their user.
- **Tokens stored as SHA-256 hashes**: session and invitation tokens are 256-bit random
  values, so a fast deterministic hash is correct (argon2 is for low-entropy passwords).
- **Emails normalized to lowercase**, enforced by CHECK constraint.
- **Deterministic constraint names** via a SQLAlchemy naming convention, so migrations can
  alter and drop constraints reliably.
- **timestamptz everywhere**, stored in UTC.

## Consequences
- Tenant isolation (Phase 4) relies on every organization-owned table carrying
  `organization_id`; this schema establishes that pattern.
- Manager-to-property assignment (spec: managers see assigned properties) is added in Phase 5.
