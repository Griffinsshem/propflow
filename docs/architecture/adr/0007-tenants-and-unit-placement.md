# ADR 0007: Tenant profiles and unit placement

## Status
Accepted

## Decisions
- One `tenant_profiles` row per tenant membership: phone (E.164), current unit, move-in
  date. Multiple tenants may share a unit (households). Leases are V2.
- Tenant invitations carry `unit_id`; acceptance places the tenant in the same transaction.
  A CHECK constraint allows a unit only on tenant invitations; composite foreign keys keep
  invitation and profile units inside the inviting organization.
- Unit occupancy follows placements: `occupied` while any active tenant is placed, `vacant`
  when the last leaves; `unavailable` (manager-set) is never overridden. Deactivation,
  moving and leaving the tenant role all free the unit through one code path
  (`release_membership`).
- Visibility: owner sees all tenants; manager only tenants in assigned properties; a
  tenant only themselves (`/tenants/me`) and their own unit.
- Phone numbers are never written to the audit log (only that the phone changed).

## Lesson recorded
Alembic autogenerate does not detect new CHECK constraints on existing tables. The
`ck_invitations_unit_only_for_tenants` constraint was added to the migration by hand and is
covered by a test that inserts a violating row.
