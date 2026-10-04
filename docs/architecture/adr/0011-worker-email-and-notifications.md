# ADR 0011: Background worker, async email and in-app notifications

## Status
Accepted (image processing and scheduled cleanup move to the worker in Phase 9b)

## Decisions
- **In-app notifications** are rows written in the same transaction as their event: a
  notification exists if and only if the event committed, so retries cannot duplicate and
  worker outages cannot lose them. Recipients follow visibility rules (responsible managers,
  else owners; the reporter; the active contractor); the actor is never notified; bodies are
  summaries, never comment text.
- **Celery with Redis** (separate logical DB from rate limiting). Tasks run in a Flask app
  context, are thin wrappers over tested functions, carry the originating request ID into
  worker logs, use `acks_late` + `reject_on_worker_lost` (a crashed task is redelivered),
  prefetch 1, JSON only, no result backend.
- **Email** is sent after commit; `BACKGROUND_TASKS=async` (production default) enqueues a
  task with exponential-backoff retries for transient transport errors. Tests and local
  development default to `sync`. A broker outage is logged and never fails the user's
  request.
- Worker entry point: `celery -A celery_worker.celery worker`.

## Known limits
- Email delivery is at-least-once: a crash after sending but before acknowledgement can
  duplicate a message. Provider idempotency keys will close this when a provider is chosen.
- Queued email bodies (including reset and invitation links) sit in the broker until
  consumed, so the broker must stay on a private network (it does on Render).
- Celery's visibility timeout (1 hour) must stay longer than any task's runtime.
