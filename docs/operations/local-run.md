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
`/tmp/propflow-storage` (if you set `TMPDIR`, the seed's reset uses that instead).

**One browser identity per person:** a normal window, a private window and a second browser can
be three different people at once. Two normal windows of one browser are the same person.

## Demo accounts (password: `correct horse battery staple`)

| Email | Who | Role |
|---|---|---|
| demo-owner@example.com | Olivia Owner | owner |
| demo-manager@example.com | Mary Manager | manager, assigned to Riverside Court only |
| demo-tenant@example.com | Tom Tenant | tenant, Riverside Court A1 |
| demo-tenant2@example.com | Tia Tenant | tenant, Riverside Court A2 |
| demo-plumber@example.com | Fred Fixit | contractor, Fixit Plumbing |
| demo-electrician@example.com | Elle Sparks | contractor, Bright Sparks Electrical |

Seeded state: "Leaking kitchen tap" (Tom, submitted), "No hot water" (Tia, urgent, assigned to
Fixit Plumbing, with the owner's comment), "Hallway light flickering" (Hillside Homes common area,
submitted, no manager assigned there).

## Who is notified (from the API's rules)

The person who acts is never notified. Reported: the property's managers, or the owners if none.
Status changed: the reporter. Comment: the reporter, responsible staff and any contractor on the
request. Work order assigned: the contractor. Work order moved: staff if the contractor moved it,
otherwise the contractor.

## 1. Owner (normal window)

- [ ] Dashboard: Properties 2, Units 4, Active tenants 2; Operations: New requests 2,
      Urgent and open 1, Awaiting acceptance 1.
- [ ] "New requests" opens Maintenance filtered to Submitted, showing exactly two requests. Reload:
      the filter stays (it lives in the address).
- [ ] Properties: Riverside Court shows Mary Manager under Managers; Hillside Homes has none.
- [ ] Contractors: Fixit Plumbing and Bright Sparks Electrical, both "can sign in".

## 2. Manager (private window)

- [ ] Bell shows unread notifications: the two tenant reports and the owner's comment on
      "No hot water" (all at Riverside Court, her property).
- [ ] Properties lists Riverside Court only. Maintenance does not list "Hallway light flickering"
      (Hillside Homes is not hers).
- [ ] Triage "Leaking kitchen tap", assign it to Fixit Plumbing with a due date next week.

## 3. Tenant (second browser, Tom)

- [ ] Dashboard: "Your home: Riverside Court · Unit A1"; Your requests: Submitted or more,
      depending on what the manager did.
- [ ] Notifications: "Maintenance request updated" for each move the manager made on his tap.
- [ ] Report a new issue and add a photo from your computer. Watch the `[worker]` log for
      `maintenance.process_attachment`: the photo goes "Processing…" then "Ready" via the real
      worker, not inline.
- [ ] Open Tia's request by its address (copy it from the owner's window): it must say it
      doesn't exist or isn't visible to you.

## 4. Contractor (sign in as Fred in the private window after the manager signs out)

- [ ] Dashboard: Your workload shows Awaiting acceptance (1 or 2), "Waiting for you" lists them.
- [ ] Open "No hot water": instructions, access notes, photos (none seeded), and the request's
      conversation through "Open the maintenance request".
- [ ] Accept, Start, then post a comment on the request, then Mark job complete.
- [ ] Open "Hallway light flickering" by its address: not visible to you.

## 5. Back as owner

- [ ] Bell: Fred's work order moves (staff are notified when the contractor acts).
- [ ] "No hot water" is In progress (completion doesn't resolve it): Mark resolved, then Close.
- [ ] Sign in as Tia: her timeline shows every step and Fred's comment; her bell has the updates.

## 6. Email, and two gaps expected today

- [ ] Team: invite a new manager to an address you make up. `python3 scripts/mailbox.py --to <it>`
      prints the invitation link; open it in a fresh private window, create the account, and land
      in Riverside Estates as manager.
- [ ] **Expected gap:** registering sends a verification email, but the frontend has no
      verify-email page yet, so its link leads to "page not found".
- [ ] **Expected gap:** the API supports "forgot password", but the frontend has no page for it
      yet, so there is no way to reset a password from the sign-in screen.

## 7. Edge cases to try on purpose

- [ ] Two windows on the same property as the owner: edit the city in one, save; edit the name in
      the other, save: the conflict notice lists the other change; "Keep my changes" saves both.
- [ ] Unit page: move a tenant out, then *immediately* type a floor and save. Known trade-off:
      if the page refreshes mid-typing, the typed value can be lost. Is it noticeable?
- [ ] Upload a file that is not an image (rename a .txt to .png): "Rejected" with a reason.

## Reporting what you find

For each surprise: the account, the page address, what you did, what you expected, what you saw,
and the matching `[api]` or `[worker]` log lines (each API line has a `request_id`).
