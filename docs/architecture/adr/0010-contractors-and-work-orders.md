# ADR 0010: Contractors and work orders

## Status
Accepted

## Decisions
- **Contractor records vs logins**: a `contractors` row is a business record; a contractor
  invitation can name the record, and acceptance links that login (`membership_id`, unique).
  Managers may act on a work order on the contractor's behalf; history records the real actor.
- **Work order workflow** (single transition table): ASSIGNED -> ACCEPTED -> IN_PROGRESS ->
  COMPLETED; ASSIGNED -> DECLINED (reason); ASSIGNED/ACCEPTED/IN_PROGRESS -> CANCELLED
  (managers, reason); DECLINED -> ASSIGNED via reassignment.
- **Synchronization**: work order events drive the linked request through one function,
  `maintenance.service.apply_linked_status`, which still validates against the request
  workflow and skips (never forces) moves that are no longer valid. Created -> request
  ASSIGNED; IN_PROGRESS -> IN_PROGRESS; DECLINED/CANCELLED -> TRIAGED (new request transition
  ASSIGNED -> TRIAGED). COMPLETED deliberately changes nothing: the manager verifies and
  resolves (spec section 5).
- **One active work order per request**: partial unique index.
- **Contractor visibility**: only work orders assigned to their own record, and through them
  the linked request (details, access notes, comments, photos). Declined/cancelled orders and
  their requests drop out of view. This adds `maintenance.read` to the contractor role,
  amending ADR 0005; the scope rule keeps it narrow.
- **Completion evidence** reuses maintenance comments and attachments (no parallel feature).
- **Overdue** is computed on read (due date passed while active), never stored.
- **Integrity**: composite foreign keys keep work orders, contractors, requests and creators
  in one organization; a CHECK limits `invitations.contractor_id` to contractor invitations
  (added to the migration by hand, see ADR 0007).

## Trade-offs
- Contractors can read the whole request thread, including tenant comments made before they
  were assigned. Internal-only notes are a candidate for V2.
- "Overdue" uses the server's UTC date; per-organization time zones come later.
