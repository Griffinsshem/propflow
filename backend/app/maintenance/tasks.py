"""Worker jobs for maintenance attachments."""

from __future__ import annotations

import uuid
from typing import Any

from celery import shared_task

from app.common.storage import StorageUnavailableError
from app.maintenance import attachments
from app.worker import bind_task_context


@shared_task(
    bind=True,
    name="maintenance.process_attachment",
    autoretry_for=(StorageUnavailableError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=8,
    acks_late=True,
)
def process_attachment(
    self: Any, attachment_id: str, organization_id: str, request_id: str | None = None
) -> None:
    bind_task_context(self, request_id)
    attachments.process_attachment(uuid.UUID(attachment_id), uuid.UUID(organization_id))
