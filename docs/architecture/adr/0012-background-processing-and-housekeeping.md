# ADR 0012: Background processing and scheduled housekeeping

## Status
Accepted

## Decisions
- **One switch, one entry point**: `BACKGROUND_TASKS` (`sync`|`async`, replacing
  `EMAIL_DELIVERY`) and `app.worker.dispatch()`. Sync mode calls the task's function directly
  in the current context (deterministic tests, local dev without a worker); async mode
  enqueues. Enqueue failures are logged and never fail the user's request.
- **Attachment processing in the worker**: `complete` checks the upload exists, marks
  PROCESSING, dispatches, returns 202; clients poll `GET .../attachments/{id}`. Rejections
  are a status with a reason. The job is idempotent (acts only on PROCESSING rows, SKIP
  LOCKED) and recovers a crash between writing the result and committing.
- **Scheduled jobs** (Celery beat): recover unfinished uploads (15 min), purge expired
  sessions, purge old notifications, remove orphaned objects (daily). All idempotent,
  batched (500), safe to run twice. Exactly one beat process is intended.
- **Orphan removal is conservative**: only keys exactly matching our naming pattern, only
  objects older than a one-day grace period, only when no READY attachment owns the key.
- Worker stdout is no longer redirected, so structured log levels stay truthful.

## Trade-offs
- The orphan scan reads up to 10,000 keys per run; at much larger scale use bucket
  inventory reports instead of listing.
- "Stuck processing" uses upload start time as a cheap heuristic; re-processing is idempotent,
  so a false positive only costs a no-op job.
