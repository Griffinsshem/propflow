# Running PropFlow locally and testing it by hand

## Start, seed, stop

| Step | Command |
|---|---|
| Start everything (Postgres and Redis must be running) | `scripts/dev.sh` |
| Add demo data (second terminal, from `backend/` with the venv active) | `python scripts/seed_demo.py` |
| Read the emails the app sent | `python3 scripts/mailbox.py` (`-n 10`, `--to address`) |
| Stop | Ctrl+C in the `dev.sh` terminal |
| Start over with an empty database | `python scripts/seed_demo.py --reset`, then seed again |

`dev.sh` runs what production runs: gunicorn (2 workers), a Celery worker and scheduler with the
commands from `render.yaml`, and a production build of the frontend. Logs are prefixed `[api]`,
`[worker]`, `[beat]` and `[web]`. Email goes to `/tmp/propflow-mail` and uploads to
`/tmp/propflow-storage`. Emails are sent by the worker, so allow a few seconds before reading them.

**Browser tests use the same ports:** stop `dev.sh` and run the API alone
(`frontend-development.md`) before `npx playwright test`.

## One browser identity per person

A normal window, a private window and a second browser are three different people. Two normal
windows of one browser are the same person. **Private-window sign-ins last only while a private
window stays open:** closing them all, or a browser restart (such as a pending update), signs
that person out. That is the browser, not PropFlow.

## Demo accounts (password: `correct horse battery staple`)

| Email | Who | Role | Email verified? |
|---|---|---|---|
| demo-owner@example.com | Olivia Owner | owner | no (registered directly) |
| demo-manager@example.com | Mary Manager | manager, Riverside Court only | yes (joined by invitation) |
| demo-tenant@example.com | Tom Tenant | tenant, Riverside Court A1 | yes (invitation) |
| demo-tenant2@example.com | Tia Tenant | tenant, Riverside Court A2 | yes (invitation) |
| demo-plumber@example.com | Fred Fixit | contractor, Fixit Plumbing | yes (invitation) |
| demo-electrician@example.com | Elle Sparks | contractor, Bright Sparks Electrical | yes (invitation) |

Seeded state: "Leaking kitchen tap" (Tom, submitted), "No hot water" (Tia, urgent, assigned to
Fixit Plumbing, with the owner's comment), "Hallway light flickering" (Hillside Homes common area,
submitted, no manager assigned there).

## Rules confirmed against the code

**Email verification.** Registering directly leaves an account unverified: the dashboard shows a
banner with "Resend email" until the emailed link is used. Accepting an emailed invitation
verifies the address (`organizations/invitations.py`: the token was delivered to that mailbox).
A password reset does not change verification. Verification links can be reopened until they
expire (verifying twice changes nothing); password reset links work once.

**Forgot password** answers the same for every address, so it cannot reveal who has an account,
but only real accounts receive an email.

**Notifications.** The person who acts is never notified. Reported: the property's managers, or
the owners if none. Status changed: the reporter. Comment: the reporter, responsible staff and any
contractor on the request. Work order assigned: the contractor. Work order moved: staff if the
contractor moved it, otherwise the contractor.

**Managers** see only properties assigned to them. A new manager's dashboard says so until an
owner assigns them from a property's page.

## The hand-test checklist

1. **Owner:** dashboard counts link to filtered lists (filters survive reload); properties,
   managers, contractors; phone validation on contractors.
2. **Manager:** notifications; only assigned properties; triage and assign a contractor.
3. **Tenant:** home on the dashboard; report an issue; a real photo goes "Processing…" then
   "Ready" via the worker (`[worker] … maintenance.process_attachment`); a fake `.png`
   (`echo "not a picture" > ~/Desktop/fake-photo.png`) is "Rejected"; comment.
4. **Contractor:** workload counts; accept, start, comment on the request, complete; decline
   another job with a reason.
5. **Owner and tenants again:** resolve and close; the tenant's timeline shows every step.
6. **Invitations:** invite an address from Team, read the link with `mailbox.py`, open it in a
   fresh private window, create the account, land in the organization.
7. **Accounts:** "Forgot password?" from sign-in, reset from the emailed link, old password
   refused, link refused the second time; verify an unverified account (Olivia) from the
   dashboard banner.
8. **Access:** another person's request address shows "not visible to you"; a tenant typing
   `/contractors` or `/settings/team` is refused.
9. **Edge cases:** two windows editing the same property show the conflict notice and keep both
   changes; phone view (F12, Ctrl+Shift+M, 360 × 800) has a one-row header, a menu with every
   section, and no sideways scrolling.

## Reporting what you find

For each surprise: the account, the page address, what you did, what you expected, what you saw,
and the matching `[api]` or `[worker]` log lines (each API line has a `request_id`).
