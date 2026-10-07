# ADR 0018: Contractor access to job photos and conversation (review of ADR 0010)

## Status
Accepted

## Context
F4 needed contractors to see the photos of the jobs they are sent to. A first analysis concluded
that contractors lacked maintenance.read, and a narrow photo endpoint on work orders was built.
Its test showed otherwise: ADR 0010 deliberately gives contractors maintenance.read, scoped to
requests linked to their own active or completed work orders. They can read those requests in
full (details, photos, comments, including earlier ones, and history), and the comment thread
is how contractors and tenants coordinate visits. The first analysis had relied on an outdated
reading of the permission table; checks now run against the live code.

## Decision
- Keep ADR 0010's design. The narrow photo endpoint was removed before release as redundant:
  less surface to secure, one source of truth for contractor visibility.
- The work order page shows the job's photos through the existing request route and links the
  assigned contractor to the request's conversation.
- The comment box states who reads comments (the tenant who reported it, staff, and any
  contractor assigned to the job), so nobody writes believing a comment is private.

## Alternative considered
Narrowing contractors to photos only. Rejected: contractors could post updates but never read
replies, so comment access would have to go too, losing contractor-tenant coordination.

## Evidence
`tests/integration/test_contractor_photo_access.py` (assigned contractor: 200; another
contractor: 404; after declining: 404) and the browser journeys "a contractor takes a tenant's
leak from assignment to completion" and "the assigned contractor sees the job's photos".
