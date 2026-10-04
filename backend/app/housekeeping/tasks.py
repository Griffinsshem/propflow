"""Scheduled housekeeping tasks (Celery beat). Thin wrappers over app.housekeeping.service."""

from __future__ import annotations

from typing import Any

import structlog
from celery import shared_task

from app.housekeeping import service
from app.worker import bind_task_context

logger = structlog.get_logger("propflow.housekeeping")


@shared_task(bind=True, name="housekeeping.recover_unfinished_uploads", acks_late=True)
def recover_unfinished_uploads(self: Any) -> None:
    bind_task_context(self, None)
    logger.info("housekeeping_finished", job=self.name, **service.recover_unfinished_uploads())


@shared_task(bind=True, name="housekeeping.purge_expired_sessions", acks_late=True)
def purge_expired_sessions(self: Any) -> None:
    bind_task_context(self, None)
    logger.info("housekeeping_finished", job=self.name, removed=service.purge_expired_sessions())


@shared_task(bind=True, name="housekeeping.purge_old_notifications", acks_late=True)
def purge_old_notifications(self: Any) -> None:
    bind_task_context(self, None)
    logger.info("housekeeping_finished", job=self.name, removed=service.purge_old_notifications())


@shared_task(bind=True, name="housekeeping.remove_orphaned_objects", acks_late=True)
def remove_orphaned_objects(self: Any) -> None:
    bind_task_context(self, None)
    logger.info("housekeeping_finished", job=self.name, removed=service.remove_orphaned_objects())
