"""Scheduled housekeeping jobs.

Every job is idempotent and works in bounded batches: running it twice (two beat processes
by mistake, or a redelivered task after a crash) is harmless.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, delete, or_, select

from app.auth.models import UserSession
from app.common.storage import StorageUnavailableError, get_storage
from app.extensions import db
from app.maintenance import attachments, tasks
from app.maintenance.models import AttachmentStatus, MaintenanceAttachment
from app.notifications.models import Notification
from app.worker import dispatch

logger = structlog.get_logger("propflow.housekeeping")

BATCH_SIZE = 500
MAX_KEYS_SCANNED = 10_000
UPLOAD_ABANDONED_AFTER = timedelta(days=1)
PROCESSING_STUCK_AFTER = timedelta(minutes=15)
SESSION_RETENTION = timedelta(days=7)
READ_NOTIFICATION_RETENTION = timedelta(days=90)
NOTIFICATION_RETENTION = timedelta(days=180)
ORPHAN_GRACE_PERIOD = timedelta(days=1)
# Only keys exactly matching our own attachment naming are ever considered for deletion.
_ATTACHMENT_KEY = re.compile(
    r"^orgs/[0-9a-f-]{36}/maintenance/[0-9a-f-]{36}/(?P<id>[0-9a-f-]{36})\.jpg$"
)


def _now() -> datetime:
    return datetime.now(UTC)


def recover_unfinished_uploads(now: datetime | None = None) -> dict[str, int]:
    """Rejects uploads started but never completed; re-queues processing that got lost."""
    now = now or _now()
    abandoned = list(
        db.session.execute(
            select(MaintenanceAttachment)
            .where(
                MaintenanceAttachment.status == AttachmentStatus.PENDING,
                MaintenanceAttachment.created_at < now - UPLOAD_ABANDONED_AFTER,
            )
            .order_by(MaintenanceAttachment.created_at)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        ).scalars()
    )
    storage = get_storage()
    for attachment in abandoned:
        attachment.status = AttachmentStatus.REJECTED
        attachment.rejection_reason = "The upload was never completed."
        try:
            storage.delete(attachments.pending_key(attachment))
        except StorageUnavailableError:
            logger.warning("pending_object_cleanup_deferred", attachment_id=str(attachment.id))
    db.session.commit()

    stuck = [
        (row[0], row[1])
        for row in db.session.execute(
            select(MaintenanceAttachment.id, MaintenanceAttachment.organization_id)
            .where(
                MaintenanceAttachment.status == AttachmentStatus.PROCESSING,
                MaintenanceAttachment.created_at < now - PROCESSING_STUCK_AFTER,
            )
            .limit(BATCH_SIZE)
        )
    ]
    db.session.rollback()
    for attachment_id, organization_id in stuck:
        dispatch(tasks.process_attachment, str(attachment_id), str(organization_id))
    return {"abandoned": len(abandoned), "requeued": len(stuck)}


def purge_expired_sessions(now: datetime | None = None) -> int:
    cutoff = (now or _now()) - SESSION_RETENTION
    doomed = (
        select(UserSession.id)
        .where(or_(UserSession.expires_at < cutoff, UserSession.revoked_at < cutoff))
        .limit(BATCH_SIZE)
    )
    removed = db.session.execute(
        delete(UserSession)
        .where(UserSession.id.in_(doomed))
        .returning(UserSession.id)
        .execution_options(synchronize_session=False)
    ).scalars()
    count = len(list(removed))
    db.session.commit()
    return count


def purge_old_notifications(now: datetime | None = None) -> int:
    now = now or _now()
    doomed = (
        select(Notification.id)
        .where(
            or_(
                and_(
                    Notification.read_at.is_not(None),
                    Notification.created_at < now - READ_NOTIFICATION_RETENTION,
                ),
                Notification.created_at < now - NOTIFICATION_RETENTION,
            )
        )
        .limit(BATCH_SIZE)
    )
    removed = db.session.execute(
        delete(Notification)
        .where(Notification.id.in_(doomed))
        .returning(Notification.id)
        .execution_options(synchronize_session=False)
    ).scalars()
    count = len(list(removed))
    db.session.commit()
    return count


def remove_orphaned_objects(now: datetime | None = None) -> int:
    """Deletes stored photos that no READY attachment owns. Conservative by design: only our
    exact key pattern, only objects older than the grace period (protects in-flight writes)."""
    cutoff = (now or _now()) - ORPHAN_GRACE_PERIOD
    storage = get_storage()
    candidates: dict[uuid.UUID, str] = {}
    for key, modified in storage.list_objects("orgs/", MAX_KEYS_SCANNED):
        match = _ATTACHMENT_KEY.match(key)
        if match is None or modified > cutoff:
            continue
        try:
            candidates[uuid.UUID(match["id"])] = key
        except ValueError:
            continue
    if not candidates:
        return 0
    owned = {
        row[0]
        for row in db.session.execute(
            select(MaintenanceAttachment.id, MaintenanceAttachment.storage_key).where(
                MaintenanceAttachment.id.in_(candidates),
                MaintenanceAttachment.status == AttachmentStatus.READY,
            )
        )
        if row[1] == candidates[row[0]]
    }
    db.session.rollback()
    removed = 0
    for attachment_id, key in candidates.items():
        if attachment_id in owned or removed >= BATCH_SIZE:
            continue
        storage.delete(key)
        removed += 1
        logger.warning("orphaned_object_removed", key=key)
    return removed
