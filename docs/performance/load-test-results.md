# Load test results

Evidence, not claims (spec section 55). Everything below was measured; anything not measured
is listed under "What this does not prove".

## 1. Query plans at realistic volume (2026-10-05)

Seeded with `backend/scripts/seed_load_data.py --orgs 50` into a dedicated `propflow_load`
database: 50 organizations, 400 properties, 16,000 units and tenants, 16,300 users,
64,000 maintenance requests, 296,012 status-history rows, 54,441 work orders, 64,000
notifications. `backend/scripts/explain_hot_queries.py` captured every SELECT the hot read
paths run, as real users of the busiest organization, and ran `EXPLAIN (ANALYZE, BUFFERS)`.

**Finding:** dashboard counters aggregated over the list queries, inheriting their display
joins. The planner cannot drop inner joins, so owner dashboards scanned platform-wide tables:
cost grew with the whole platform, not with the organization being viewed.

**Fix:** visibility rules became one join-free condition per resource (`_scope_condition`),
shared by the list queries (plus display joins) and the counters (no joins).

| Owner operations dashboard | Before | After |
|---|---|---|
| Request counters | 6.48 ms, seq scan of all 16,300 memberships | 0.78 ms, index scan within the org |
| Work order counters | 15.87 ms, seq scan of all 64,000 requests | 0.44 ms, index scan within the org |
| Whole dashboard (end to end) | 36.8 ms | 17.8 ms |

All other hot paths used index scans on large tables; remaining sequential scans were on
small tables (`contractors`, `property_assignments`) where they are the cheapest plan.

## 2. Baseline load test (2026-10-05)

`load-tests/journeys.js`, profile `baseline`: 2 min ramp, 8 min hold, 30 s ramp-down.

| Scenario | Virtual users | Journey (with human think time) |
|---|---|---|
| Tenants | 40 | dashboard, own requests, request detail, unread count; reports an issue on 1 visit in 5 |
| Managers | 15 | operations dashboard, submitted inbox, opens and triages a request, overdue work orders |
| Contractors | 15 | contractor dashboard, then accepts, starts or completes one job |
| Owners | 5 | organization dashboard, operations dashboard, request list |
| Cold logins | 1 per second | a new browser logging in, cycling through all 16,000 tenants |

Every rate limit was enabled. Each virtual user had its own client IP via
`X-Forwarded-For` (the server trusted one proxy hop), as real users would in production.
Writes used optimistic-concurrency versions and CSRF tokens exactly as the frontend will.

### Overall

| Metric | Result |
|---|---|
| Requests | 12,434 in 650 s (19.1 per second) |
| Failed requests | 0.00% |
| Server errors (5xx) in API log | 0 |
| Rate-limited (429) / conflict (409) responses | 0 / 0 |
| Checks passed | 100.00% (12,434 / 12,434) |
| Host CPU (average, `vmstat`) | 19% user, 3% system, 69% idle |
| Swap activity | 24 KiB in total over the run (negligible) |

### Per endpoint

| Endpoint | Requests | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | p95 budget |
|---|---:|---:|---:|---:|---:|---|
| `GET /dashboard/contractor` | 525 | 56.5 | 83.9 | 102.5 | 319.2 | 300, pass |
| `GET /dashboard/operations` | 575 | 159.1 | 216.5 | 239.6 | 442.6 | 300, pass |
| `GET /dashboard/organization` | 166 | 33.5 | 51.9 | 67.1 | 96.0 | 300, pass |
| `GET /dashboard/tenant` | 1,775 | 51.2 | 74.4 | 106.9 | 386.8 | 300, pass |
| `GET /maintenance` | 2,350 | 35.2 | 62.2 | 93.3 | 387.8 | 300, pass |
| `GET /maintenance/{id}` | 2,163 | 27.6 | 40.3 | 70.1 | 396.0 | 300, pass |
| `GET /notifications/unread-count` | 2,184 | 21.8 | 32.5 | 56.1 | 114.7 | 200, pass |
| `GET /work-orders` | 934 | 56.8 | 88.1 | 102.4 | 280.4 | 300, pass |
| `POST /auth/login` | 75 | 308.9 | 437.5 | 445.5 | 455.6 | 1000, pass |
| `POST /auth/login (new browser)` | 480 | 274.3 | 312.4 | 333.8 | 535.0 | 1000, pass |
| `POST /maintenance` | 337 | 72.1 | 96.9 | 115.6 | 132.6 | 500, pass |
| `POST /maintenance/{id}/status` | 409 | 72.2 | 95.9 | 120.5 | 178.4 | 500, pass |
| `POST /work-orders/{id}/status` | 461 | 78.8 | 108.3 | 123.5 | 140.2 | 500, pass |

Budgets are initial targets set before the run, not spec requirements.

### Interpretation

- Reads and writes are comfortably inside budget with the host mostly idle, so these
  figures reflect the application rather than a saturated machine.
- Login is the costliest operation by design: full-strength Argon2id (argon2-cffi defaults,
  about 64 MiB per hash) costs roughly 0.3 s per login. This is the price of making leaked
  password hashes expensive to crack.
- **Open item:** the manager operations dashboard (p50 159 ms) is about 3x the other
  dashboards. EXPLAIN measured about 15 ms of database time for its queries, so most of the
  cost is unexplained. A known contributor: its "recent" and "recently updated" queries join
  every in-scope request (721 rows for one manager) before sorting and limiting to 5. The
  remainder is to be profiled before any change is made.

## Environment

| Component | Version / setting |
|---|---|
| Host | Dell Latitude 7300, Intel Core i7-8665U (4 cores, 8 threads), 15 GiB RAM, 5.4 GiB available at start |
| API | gunicorn 26.2.0, 4 sync workers, `APP_ENV=development`, `BACKGROUND_TASKS=sync`, `EMAIL_BACKEND=disabled` |
| Database | PostgreSQL 16.15, local, default configuration |
| Cache / limits | Redis 7.0.15, local |
| Load generator | k6 v2.3.0, on the same host |

## What this does not prove

- **Production capacity.** Render instances have different CPU, memory and limits than this
  laptop; production numbers must be measured on the deployed stack.
- **Network latency.** All traffic was on localhost. Real users add the Vercel proxy hop and
  the round trip from Kenya to the hosting region.
- **Isolation.** k6, the API, Postgres and Redis shared one machine and competed for CPU.
- **Production logging and background work.** Development logging (console renderer, debug
  level) is slower than production JSON logs; notifications and email ran inline rather
  than on the Celery worker.
- **Scale beyond this dataset.** 64,000 requests across 50 organizations fit in memory.
  Larger datasets, cold caches and bigger organizations are untested.
- **Limits of the system.** This is a baseline at human pace (19 requests per second), not a
  stress test; the point where latency or errors climb has not been measured yet.
- **Contended writes and uploads.** No two users edited the same record (no 409 paths
  exercised), and photo uploads to object storage were not included.

## Reproducing

1. Create `propflow_load`, run migrations, seed: `python -m scripts.seed_load_data --orgs 50`.
2. Start the API: `DATABASE_URL=<...>/propflow_load TRUSTED_PROXY_COUNT=1
   EMAIL_BACKEND=disabled gunicorn "app:create_app()" --workers 4 --bind 127.0.0.1:8000`.
3. Clear rate-limit counters (`redis-cli -n 2 flushdb`), then from the repo root:
   `k6 run -e PROFILE=baseline load-tests/journeys.js`.
4. Summarize: `python3 load-tests/summarize.py load-tests/results/<run>.json`.

Each run changes the data (requests triaged, jobs advanced); reseed before runs that will
be compared.
