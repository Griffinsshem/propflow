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

## 3. Profiling the operations dashboard (2026-10-05)

The baseline showed `GET /dashboard/operations` at about 3x the other dashboards. Every
request log line now records `db_queries` and `db_ms` (`app/common/db_timing.py`), and
`load-tests/route_timings.py` splits each route's server time into database and
application time. Profile runs: `PROFILE=profile` (1 min ramp, 3 min hold, baseline mix).

**Finding:** database-bound (62.6 of 96.0 ms at p50), 8 queries, no N+1. EXPLAIN showed the
list-style queries (recent requests, recently updated, overdue work orders) joining display
tables for all 721 requests in a manager's scope before sorting and keeping 5. The planner
estimated 4 rows per property against 180 actual (`organization_id` and `property_id` are
correlated). Extended statistics (`CREATE STATISTICS ... (dependencies)`) were tried and
**did not change the estimate or the plan**, because the property IDs arrive at run time from
the assignment subquery, so the experiment was reverted.

**Fix:** choose the page first, then join (`paginate_keys`, `request_rows`,
`work_order_rows`). The page's IDs come from the join-free scoped query (authorization is
unchanged); display joins then run for the page only. Applied to the maintenance and work
order lists and every dashboard list.

### Manager dashboard query plans (no load)

| Query | Before | After |
|---|---:|---:|
| Recent requests | 13.10 ms (joins x721) | 0.88 + 0.59 ms (5 IDs, joins x5) |
| Recently updated | 11.59 ms (joins x721) | 0.67 + 0.29 ms |
| Overdue work orders | 11.24 ms | 3.08 + 0.44 ms |
| Work order counters | 5.24 ms | 3.77 ms (must visit every in-scope job) |
| Request counters | 1.58 ms | 1.11 ms |
| **Total** | **42.7 ms** | **10.8 ms** |

### `GET /dashboard/operations` under load (server-side, profile runs)

| Metric | Before | After |
|---|---:|---:|
| Database p50 / p95 | 62.6 / 138.8 ms | 34.0 / 67.1 ms |
| Total p50 / p95 | 96.0 / 209.4 ms | 79.3 / 141.7 ms |
| k6 p95 (client-side) | 216.4 ms | 148.5 ms |
| Queries per request | 8 | 11 |

### Trade-off, measured

Page-first adds one round trip per list. On endpoints whose scope is already small, p50 moved
by a few milliseconds, within run-to-run noise on this host but in a consistent direction:
`GET /maintenance` 26.9 → 31.0 ms, tenant dashboard 40.1 → 43.3 ms, contractor dashboard
39.1 → 41.4 ms (`GET /work-orders` 39.3 → 36.6 ms). Accepted deliberately: the old shape's
join cost grows with portfolio size, the new one is bounded by page size. The growth claim is
reasoned from the plans, not measured at a larger scale.

### Where the time goes now

Application time (42.4 ms p50) now exceeds database time (34.0 ms) for this endpoint. Under
load, database time is about 3x the quiet-machine EXPLAIN total, which is consistent with CPU
contention on a host shared by 4 workers, Postgres, Redis, k6 and Argon2 logins. The next lever
would be merging the dashboard's queries into fewer round trips. Not pursued: every endpoint
is within budget with about 2x headroom at p95, so the next step is a stress test to find the
real limit rather than further tuning.

## 4. Stress test: one instance, 4 sync workers (2026-10-05)

`PROFILE=stress`: journeys started at a rising rate in steps (5, 10, 15, 20, 30, 40, 50, 60
per second; 15 s ramp + 60 s hold each), baseline mix (50% tenants, 20% managers, 15%
contractors, 5% owners, 10% cold logins), no think time, all rate limits on. Status changes
accept 409 (optimistic-concurrency races) as correct. The run aborts once p95 exceeds 3 s or
errors exceed 5%. Per-step figures: `load-tests/stress_report.py` over the k6 CSV output.

| Step | Journeys/s | Achieved req/s | p50 ms | p95 ms | p99 ms | 5xx / timeouts / 429 | Dropped | CPU busy |
|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1 | 5 | 19.7 | 43 | 286 (login warm-up) | 410 | 0 / 0 / 0 | 0 | 31% |
| 2 | 10 | 38.2 | 40 | 129 | 279 | 0 / 0 / 0 | 0 | 33% |
| 3 | 15 | 58.3 | 41 | 117 | 260 | 0 / 0 / 0 | 0 | 46% |
| 4 | 20 | 77.9 | 47 | 132 | 251 | 0 / 0 / 0 | 0 | 58% |
| 5 | 30 | 113.3 | 104 | 247 | 325 | 0 / 0 / 0 | 0 | 65% |
| 6 | 40 | 113.5 | 715 | 4,882 | 6,193 | 0 / 0 / 0 | 422 | 73% |

Aborted 11 s into step 7 (p95 over 3 s). No 5xx, timeouts, rate limiting, worker timeouts,
pool errors or swapping at any step.

**Ceiling: about 113 requests per second.** Throughput stopped rising between steps 5 and 6.
**Knee: between 78 and 113 requests per second**: latency was flat through step 4 and
doubled at step 5.

**Bottleneck: worker slots, not CPU or database.** Server-side times stayed at baseline
levels throughout (operations dashboard p95 124 ms, database p95 at most 59 ms on any route)
while client-side p95 reached several seconds: requests were queued waiting for one of the
4 sync workers. Throughput matches workers / mean service time (4 / ~35 ms ≈ 113 req/s).
CPU was 65-73% busy: each sync worker uses one core, so 4 workers cannot use all 8 threads.

**Login cost under load:** each login holds a worker for about 200 ms (Argon2), roughly 8x
an average request; at step 5, cold logins alone consumed about 15% of worker capacity. Login
bursts compete with all other traffic.

**Overload behaviour:** past the ceiling, sync gunicorn queues requests (socket backlog)
rather than failing fast, so users see multi-second waits instead of errors. Production must
run below the knee, with scaling triggered on latency or worker utilisation.

**Hypothesis to confirm:** more workers raise the ceiling until CPU saturates (section 5).

## 5. Stress test: one instance, 8 sync workers (2026-10-05)

Identical profile and data; only `--workers 8` changed (connection pools at defaults).

| Step | Journeys/s | Achieved req/s | p50 ms | p95 ms | p99 ms | 5xx / timeouts / 429 | Dropped | CPU busy | Swap KiB/s |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 1 | 5 | 19.6 | 42 | 282 (login warm-up) | 469 | 0 / 0 / 0 | 0 | 36% | 3 |
| 2 | 10 | 38.1 | 40 | 134 | 303 | 0 / 0 / 0 | 0 | 40% | 5 |
| 3 | 15 | 57.6 | 38 | 116 | 274 | 0 / 0 / 0 | 0 | 49% | 0 |
| 4 | 20 | 77.2 | 36 | 120 | 278 | 0 / 0 / 0 | 0 | 62% | 0 |
| 5 | 30 | 114.3 | 30 | 115 | 291 | 0 / 0 / 0 | 0 | 74% | 0 |
| 6 | 40 | 147.7 | 27 | 112 | 214 | 0 / 0 / 0 | 0 | 79% | 0 |
| 7 | 50 | 176.7 | 42 | 249 | 349 | 0 / 0 / 0 | 0 | 91% | 1 |
| 8 | 60 | 119.4 | 2,328 | 10,082 | 11,918 | 0 / 0 / 0 | 1,716 | 99% | 2,245 |

56,425 requests in total; 0 failed. Six 409s at step 8 (optimistic-concurrency races,
correctly rejected).

### Comparison

| | 4 workers | 8 workers |
|---|---:|---:|
| Highest throughput with flat p95 | 77.9 req/s | 147.7 req/s |
| Peak throughput | 113.5 req/s | 176.7 req/s |
| Knee | 78-113 req/s | 148-177 req/s |
| CPU busy at the knee | 65% | 79-91% |
| Limiting resource | worker slots | CPU, then memory |

**Hypothesis confirmed, with a limit:** throughput scales with workers until CPU saturates.
Doubling workers raised the ceiling about 56%, not 100%, because CPU reached 91% at step 7.
Server-side times stayed at baseline levels (operations dashboard p95 140 ms, database p95
at most 65 ms); login p50 rose from 196 to 267 ms as Argon2 competed for CPU.

**Collapse past saturation:** at step 8, CPU reached 99% and swapping began; throughput fell
*below* the previous step (176.7 → 119.4 req/s). The overload behaviour is real; where it
occurred is specific to this host (8 workers, Postgres, Redis and 463 k6 VUs sharing 15 GiB).

## 6. Production starting configuration (derived from sections 4-5)

| Setting | Starting value | Reason |
|---|---|---|
| gunicorn sync workers | 2 x vCPU | requests spend ~35-45% of their time waiting on the database, so a core serves about two workers before CPU limits |
| DB pool per worker | `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=0` | a sync worker serves one request, using one connection, at a time; total = instances x workers x 2 |
| Operating point | at most ~70% of the measured knee per instance | past saturation throughput falls rather than levels off |
| Scaling | add instances (horizontal) | stateless API: sessions in Postgres, rate limits in Redis |
| Alerting | latency (p95) and CPU, not error rate | overload showed as queueing delay with zero errors |

Back-of-envelope, not measured: the baseline's 75 human-paced users produced 19 req/s; ~105
req/s (70% of the 8-worker knee) would correspond to roughly 400 concurrently active users
per instance on this host. Every value above must be re-measured with the stress profile
against the deployed stack, whose CPU, memory and network differ from this laptop.

## Updated: what these tests do not prove

- Production capacity, network latency (Vercel proxy hop, Kenya to the hosting region),
  production logging, or Celery-based background work: see section 2.
- Behaviour on Render instance sizes: worker counts and the knee depend on vCPU and memory.
- Larger datasets than 64,000 requests across 50 organizations, or cold caches.
- Isolation: k6 shared the host; at high load its VUs competed for CPU and memory.
