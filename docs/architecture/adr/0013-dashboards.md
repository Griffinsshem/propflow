# ADR 0013: Dashboards

## Status
Accepted

## Decisions
- Four endpoints matching the spec pages: operations (owner/manager), organization
  (owner), tenant, contractor.
- **Same scope as the lists**: every counter aggregates over the scoped query its list page
  uses (`visible_requests`, `visible_work_orders`), so a dashboard cannot count a record the
  viewer could not open. A property filter outside the caller's scope returns 404.
- **Few queries**: each counter block is a single `COUNT(*) FILTER (WHERE ...)` aggregate;
  organization totals are one statement of scalar subqueries. A test asserts the number of
  SQL statements does not change as data grows (guards against N+1).
- New indexes: `(organization_id, updated_at)` on requests; partial `(organization_id,
  due_date)` on active work orders.
- Real data only; empty organizations return zeros and empty lists.

## Deferred, deliberately
- Caching: not added until measurements show it is needed (spec: do not cache because Redis
  is available). If added, keys must include organization and viewer scope.
- `EXPLAIN ANALYZE` at realistic volume runs in Phase 11 with seeded load-test data; plans on
  a near-empty database are not meaningful.
- "This month" is computed in UTC; organization time zones are a later enhancement.
