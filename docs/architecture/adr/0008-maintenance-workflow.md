# ADR 0008: Maintenance requests and the status workflow

## Status
Accepted (attachments follow in Phase 7b)

## Decisions
- **Single transition table** (`app/maintenance/workflow.py`): every allowed `from -> to`
  pair names the permission it requires and whether a reason is mandatory. Anything else
  returns `409 INVALID_STATUS_TRANSITION`. Beyond the spec's linear lifecycle: reopen
  (`resolved -> in_progress`) and early close (`submitted|triaged -> closed`), both with
  required reasons; `waiting` also requires a reason.
- **History**: one row per change (from, to, actor, reason), written in the same transaction
  as the change, alongside an audit entry.
- **`allowed_transitions`** on single-request reads tells the UI which actions this caller may
  take, computed from the same table, so the frontend never re-implements the rules.
- **Tenants never choose a location**: their unit and property come from their tenant
  profile. Staff must reference a unit or property they can see.
- **Visibility**: owner all; manager assigned properties; tenant only their own reports;
  contractor none until work orders (Phase 8).
- **Comments** are plain text stored verbatim, served only as JSON with `nosniff`, and
  escaped by the UI at render time (escape-on-output). Control characters are rejected
  (NUL would otherwise cause a database error). Comments are immutable; closed requests
  accept no new comments.
- **Integrity**: composite foreign keys keep each request's property and reporter inside its
  organization and its unit inside its property. Optimistic concurrency (`version`) on edits
  and status changes.
