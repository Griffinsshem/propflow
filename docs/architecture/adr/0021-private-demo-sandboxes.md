# ADR 0021: A private demo sandbox per visitor

## Status
Accepted and implemented.

## Context
The landing page should let anyone try PropFlow without registering. Shared demo accounts
on a public site let visitors overwrite each other's data, lock each other out by changing
the password, and send invitations to any address through our email account (a spam risk
that could get it suspended).

## Decision

### A sandbox per visitor
- `POST /api/v1/demo` creates a demo organization for that visitor only, signs them in as its
  owner through the normal session code, and answers like a sign-in. No password exists.
- The sandbox is built **through the services** (properties, units, tenants, contractors,
  requests, work orders, comments), so every rule applies and notifications appear naturally:
  two properties, four units, two tenants, a manager, a contractor, and requests that are
  submitted, in progress with a work order, and resolved.
- People in the sandbox are new users with addresses on the reserved `.invalid` domain
  (`demo-<id>@demo.propflow.invalid`), which can never receive mail. They have unusable
  passwords and are marked verified.
- `POST /api/v1/demo/view-as {role}` switches the visitor's session to the sandbox's owner,
  manager, tenant or contractor. It works only for a demo session, and only inside its own
  sandbox.

### Marked, limited and short-lived
- Migration: `organizations.is_demo`, `organizations.demo_expires_at`, `users.is_demo`.
- A sandbox lives 24 hours; its sessions expire at the same moment.
- Starting a demo is rate-limited per visitor IP (reliable since ADR 0020).
- In a demo organization the API refuses, with code `DEMO_RESTRICTED`: invitations, photo
  uploads, creating further organizations, and password or email changes.

### Email: two independent guards
1. Demo organizations cannot create invitations (above).
2. `send_email()`, the single place email leaves the system, drops any recipient on the
   `.invalid` domain and logs `demo_email_suppressed`.

### No audit rows from demos
`audit_logs` is append-only and references organizations and users, so any audit row would
make a sandbox impossible to delete. `audit.record` skips writes for demo organizations and
demo users. The audit log remains complete for every real organization.

### Expiry and deletion
- `flask demo purge-expired` deletes expired sandboxes. For each one it deletes rows with that
  `organization_id` from every table, in reverse dependency order taken from the SQLAlchemy
  metadata (so `RESTRICT` foreign keys are satisfied), then the organization, then its demo
  users (their sessions cascade). It refuses to touch any organization without `is_demo`.
- A test creates a sandbox, purges it, and asserts that no row anywhere still references it.
- A scheduled GitHub Actions workflow runs the purge, and the housekeeping jobs the free plan
  lacks (ADR 0019): expired sessions and old notifications. It needs `DATABASE_URL` as a
  repository secret.

### Frontend
- "Try the live demo" on the landing page (the reserved spot) starts a sandbox and opens the
  dashboard.
- Inside a demo, a banner says it is a private demo, when it expires, and offers "View as".

## Consequences
- Visitors never see each other's data, and no shared credential exists.
- No email can leave a demo, by two independent mechanisms.
- Demo actions are not audited; real organizations are unaffected.
- Sandboxes are deleted within an hour of expiry, keeping the free database small.
- One more scheduled job, and one more secret (`DATABASE_URL`) in GitHub.
