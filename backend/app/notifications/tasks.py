"""Background tasks. Each is thin: it binds log context and calls a plain, tested function."""

from __future__ import annotations

from typing import Any

import structlog
from celery import shared_task

from app.notifications.email import EmailMessage, EmailTransportError, deliver_now


@shared_task(
    bind=True,
    name="notifications.deliver_email",
    autoretry_for=(EmailTransportError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=8,
    acks_late=True,
)
def deliver_email(
    self: Any, to: str, subject: str, body: str, request_id: str | None = None
) -> None:
    # The originating request ID ties API logs and worker logs together.
    structlog.contextvars.bind_contextvars(
        request_id=request_id, task_id=self.request.id, task=self.name
    )
    deliver_now(EmailMessage(to=to, subject=subject, body=body))
