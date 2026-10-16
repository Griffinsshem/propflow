"""Maintenance photo attachments.

Flow: start (presigned PUT) -> browser uploads to storage -> complete (marks PROCESSING and
dispatches the worker job) -> worker verifies and sanitizes -> READY or REJECTED.
Clients poll GET .../attachments/{id} until the status settles.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from flask import g, has_request_context
from sqlalchemy import func, select

from app.audit import service as audit
from app.authz.context import OrgContext
from app.common.errors import ConflictError, NotFoundError
from app.common.storage import get_storage
from app.demo.guards import ensure_not_demo
from app.extensions import db
from app.maintenance import images, repository
from app.maintenance.models import (
    AttachmentStatus,
    MaintenanceAttachment,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.worker import dispatch

MAX_ATTACHMENTS_PER_REQUEST = 10
UPLOAD_URL_TTL_SECONDS = 300
DOWNLOAD_URL_TTL_SECONDS = 300
SETTLED = frozenset({AttachmentStatus.READY, AttachmentStatus.PROCESSING})


def _now() -> datetime:
    return datetime.now(UTC)


def pending_key(attachment: MaintenanceAttachment) -> str:
    return f"pending/{attachment.organization_id}/{attachment.id}"


def final_key(attachment: MaintenanceAttachment) -> str:
    return (
        f"orgs/{attachment.organization_id}/maintenance/{attachment.request_id}/{attachment.id}.jpg"
    )


def attachment_view(
    attachment: MaintenanceAttachment, download_url: str | None = None
) -> dict[str, Any]:
    return {
        "id": attachment.id,
        "status": attachment.status,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "width": attachment.width,
        "height": attachment.height,
        "rejection_reason": attachment.rejection_reason,
        "uploaded_by_membership_id": attachment.uploaded_by_membership_id,
        "created_at": attachment.created_at,
        "ready_at": attachment.ready_at,
        "download_url": download_url,
    }


def _visible_request(context: OrgContext, request_id: uuid.UUID) -> MaintenanceRequest:
    row = repository.get_visible_request(context, request_id)
    if row is None:
        raise NotFoundError()
    return row[0]


def _active_count(organization_id: uuid.UUID, request_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(MaintenanceAttachment)
        .where(
            MaintenanceAttachment.organization_id == organization_id,
            MaintenanceAttachment.request_id == request_id,
            MaintenanceAttachment.status != AttachmentStatus.REJECTED,
        )
    )
    return int(db.session.execute(stmt).scalar_one())


def start_upload(
    context: OrgContext, request_id: uuid.UUID, *, content_type: str, size_bytes: int
) -> dict[str, Any]:
    ensure_not_demo(context.organization_id)
    request = _visible_request(context, request_id)
    if request.status == MaintenanceStatus.CLOSED:
        raise ConflictError("Closed requests cannot receive new attachments.")
    if _active_count(context.organization_id, request.id) >= MAX_ATTACHMENTS_PER_REQUEST:
        raise ConflictError(
            f"A request can have at most {MAX_ATTACHMENTS_PER_REQUEST} attachments."
        )
    attachment = MaintenanceAttachment(
        organization_id=context.organization_id,
        request_id=request.id,
        uploaded_by_membership_id=context.membership_id,
        status=AttachmentStatus.PENDING,
        content_type=content_type,
        declared_size_bytes=size_bytes,
    )
    db.session.add(attachment)
    db.session.flush()
    url = get_storage().presigned_put(pending_key(attachment), content_type, UPLOAD_URL_TTL_SECONDS)
    db.session.commit()
    return {
        "attachment": attachment_view(attachment),
        "upload": {
            "method": "PUT",
            "url": url,
            "headers": {"Content-Type": content_type},
            "expires_in": UPLOAD_URL_TTL_SECONDS,
        },
    }


def _locked_own_attachment(
    context: OrgContext, request_id: uuid.UUID, attachment_id: uuid.UUID
) -> MaintenanceAttachment:
    stmt = (
        select(MaintenanceAttachment)
        .where(
            MaintenanceAttachment.organization_id == context.organization_id,
            MaintenanceAttachment.request_id == request_id,
            MaintenanceAttachment.id == attachment_id,
        )
        .with_for_update()
    )
    attachment = db.session.execute(stmt).scalar_one_or_none()
    # Only the uploader may finalize a pending upload; anyone else sees 404.
    if attachment is None or attachment.uploaded_by_membership_id != context.membership_id:
        raise NotFoundError()
    return attachment


def _reject(attachment: MaintenanceAttachment, reason: str, delete_key: str | None) -> None:
    if delete_key is not None:
        get_storage().delete(delete_key)
    attachment.status = AttachmentStatus.REJECTED
    attachment.rejection_reason = reason[:200]
    audit.record(
        "maintenance.attachment_rejected",
        "maintenance_request",
        attachment.request_id,
        organization_id=attachment.organization_id,
        details={"attachment_id": str(attachment.id), "reason": attachment.rejection_reason},
    )


def complete_upload(
    context: OrgContext, request_id: uuid.UUID, attachment_id: uuid.UUID
) -> dict[str, Any]:
    """Confirms the upload arrived and hands it to the worker. Idempotent."""
    _visible_request(context, request_id)
    attachment = _locked_own_attachment(context, request_id, attachment_id)
    if attachment.status == AttachmentStatus.REJECTED:
        raise ConflictError("This upload was rejected. Start a new upload.")
    if attachment.status in SETTLED:
        db.session.commit()  # releases the row lock
        return attachment_view(attachment)

    source = pending_key(attachment)
    size = get_storage().size(source)
    if size is None:
        raise ConflictError("The file has not been uploaded yet.")
    if size > images.MAX_UPLOAD_BYTES:
        _reject(attachment, "The file is larger than 10 MB.", source)
        db.session.commit()
        return attachment_view(attachment)

    attachment.status = AttachmentStatus.PROCESSING
    db.session.commit()
    from app.maintenance import tasks  # local import: the tasks module imports this one

    trace_id = g.get("request_id") if has_request_context() else None
    dispatch(
        tasks.process_attachment,
        str(attachment.id),
        str(attachment.organization_id),
        request_id=trace_id,
    )
    return attachment_view(attachment)  # final state in sync mode, PROCESSING in async mode


def process_attachment(attachment_id: uuid.UUID, organization_id: uuid.UUID) -> None:
    """Worker job: verify and sanitize one upload.

    Idempotent: anything not PROCESSING is left alone, and SKIP LOCKED stops two workers from
    racing. If a previous run wrote the result but crashed before committing, the result is
    picked up instead of the (already deleted) original.
    """
    stmt = (
        select(MaintenanceAttachment)
        .where(
            MaintenanceAttachment.id == attachment_id,
            MaintenanceAttachment.organization_id == organization_id,
        )
        .with_for_update(skip_locked=True)
    )
    attachment = db.session.execute(stmt).scalar_one_or_none()
    if attachment is None or attachment.status != AttachmentStatus.PROCESSING:
        db.session.rollback()
        return

    storage = get_storage()
    source, destination = pending_key(attachment), final_key(attachment)
    if storage.size(source) is not None:
        read_key, declared_type = source, attachment.content_type
    elif storage.size(destination) is not None:
        read_key, declared_type = destination, "image/jpeg"
    else:
        _reject(attachment, "The uploaded file is missing.", None)
        db.session.commit()
        return

    try:
        data = storage.read(read_key, images.MAX_UPLOAD_BYTES)
        if len(data) > images.MAX_UPLOAD_BYTES:
            raise images.ImageRejected("The file is larger than 10 MB.")
        processed, width, height = images.sanitize_image(data, declared_type)
    except images.ImageRejected as exc:
        _reject(attachment, str(exc), read_key)
        db.session.commit()
        return

    storage.write(destination, processed, "image/jpeg")
    if read_key == source:
        storage.delete(source)
    attachment.status = AttachmentStatus.READY
    attachment.storage_key = destination
    attachment.content_type = "image/jpeg"
    attachment.size_bytes = len(processed)
    attachment.width, attachment.height = width, height
    attachment.ready_at = _now()
    audit.record(
        "maintenance.attachment_added",
        "maintenance_request",
        attachment.request_id,
        organization_id=attachment.organization_id,
        details={"attachment_id": str(attachment.id)},
    )
    db.session.commit()


def get_attachment(
    context: OrgContext, request_id: uuid.UUID, attachment_id: uuid.UUID
) -> dict[str, Any]:
    """Ready photos are visible to everyone who can see the request; unfinished ones only to
    their uploader, who polls this endpoint until the status settles."""
    _visible_request(context, request_id)
    stmt = select(MaintenanceAttachment).where(
        MaintenanceAttachment.organization_id == context.organization_id,
        MaintenanceAttachment.request_id == request_id,
        MaintenanceAttachment.id == attachment_id,
    )
    attachment = db.session.execute(stmt).scalar_one_or_none()
    if attachment is None or (
        attachment.status != AttachmentStatus.READY
        and attachment.uploaded_by_membership_id != context.membership_id
    ):
        raise NotFoundError()
    url = None
    if attachment.status == AttachmentStatus.READY and attachment.storage_key:
        url = get_storage().presigned_get(attachment.storage_key, DOWNLOAD_URL_TTL_SECONDS)
    return attachment_view(attachment, url)


def list_attachments(context: OrgContext, request_id: uuid.UUID) -> list[dict[str, Any]]:
    """Authorization happens here, before any short-lived download URL is generated."""
    _visible_request(context, request_id)
    stmt = (
        select(MaintenanceAttachment)
        .where(
            MaintenanceAttachment.organization_id == context.organization_id,
            MaintenanceAttachment.request_id == request_id,
            MaintenanceAttachment.status == AttachmentStatus.READY,
        )
        .order_by(MaintenanceAttachment.created_at, MaintenanceAttachment.id)
        .limit(MAX_ATTACHMENTS_PER_REQUEST)
    )
    storage = get_storage()
    return [
        attachment_view(item, storage.presigned_get(item.storage_key, DOWNLOAD_URL_TTL_SECONDS))
        for item in db.session.execute(stmt).scalars()
        if item.storage_key
    ]
