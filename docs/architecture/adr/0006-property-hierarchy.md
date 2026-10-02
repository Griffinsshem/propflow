# ADR 0006: Property hierarchy, database-level tenant integrity and optimistic concurrency

## Status
Accepted

## Decisions
- **Hierarchy**: Organization -> Property -> optional Building -> Unit. Small properties
  skip buildings (`units.building_id` is nullable).
- **Composite foreign keys carry `organization_id` down the hierarchy**:
  `buildings(property_id, organization_id) -> properties(id, organization_id)`,
  `units(building_id, property_id) -> buildings(id, property_id)`, and
  `property_assignments(membership_id, organization_id) -> organization_memberships`.
  The database rejects cross-organization links even if application code is wrong.
- **Manager scope**: managers see only properties assigned to them (`property_assignments`)
  and the units inside them. Visibility rules live in one module
  (`app/properties/repository.py`). Out-of-scope records return 404.
- **Optimistic concurrency** on properties and units: a `version` column (SQLAlchemy
  `version_id_col`) plus a required `version` field on PATCH. Stale writes return 409
  instead of silently overwriting newer changes.
- **Delete vs archive**: DELETE succeeds only for empty properties (RESTRICT foreign keys);
  otherwise 409 and the client archives (`status: archived`). History is never cascaded away.
- Assignments use ON DELETE CASCADE: they are configuration, not history; the audit log
  records every assign/unassign.

## Trade-offs
- Composite keys add an extra unique index per parent table; worth it for an invariant
  that cannot be bypassed.
- Clients must round-trip `version`; the frontend gets it from every read.
- A stale assignment can remain if a manager's role changes; it grants nothing because
  scope checks also require the manager role. Cleanup on role change is a follow-up.
