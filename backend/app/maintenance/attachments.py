"""Maintenance photo attachments: presigned direct upload, then server-side verification."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.audit import service as audit
from app.authz.context import OrgContext
from app.common.errors import ConflictError, NotFoundError, RequestValidationError
from app.common.storage import get_storage
from app.extensions import db
from app.maintenance import images, repository
from app.maintenance.models import (
    AttachmentStatus,
    MaintenanceAttachment,
    MaintenanceRequest,
    MaintenanceStatus,
)

MAX_ATTACHMENTS_PER_REQUEST = 10
UPLOAD_URL_TTL_SECONDS = 300
DOWNLOAD_URL_TTL_SECONDS = 300


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
        .with_for_update()  # concurrent completes of one upload are serialized
    )
    attachment = db.session.execute(stmt).scalar_one_or_none()
    # Only the uploader may finalize a pending upload; anyone else sees 404.
    if attachment is None or attachment.uploaded_by_membership_id != context.membership_id:
        raise NotFoundError()
    return attachment


def complete_upload(
    context: OrgContext, request_id: uuid.UUID, attachment_id: uuid.UUID
) -> dict[str, Any]:
    _visible_request(context, request_id)
    attachment = _locked_own_attachment(context, request_id, attachment_id)
    if attachment.status == AttachmentStatus.READY:
        db.session.commit()  # idempotent; releases the row lock
        return attachment_view(attachment)
    if attachment.status == AttachmentStatus.REJECTED:
        raise ConflictError("This upload was rejected. Start a new upload.")

    storage = get_storage()
    source = pending_key(attachment)
    size = storage.size(source)
    if size is None:
        raise ConflictError("The file has not been uploaded yet.")
    try:
        if size > images.MAX_UPLOAD_BYTES:
            raise images.ImageRejected("The file is larger than 10 MB.")
        data = storage.read(source, images.MAX_UPLOAD_BYTES)
        if len(data) > images.MAX_UPLOAD_BYTES:
            raise images.ImageRejected("The file is larger than 10 MB.")
        processed, width, height = images.sanitize_image(data, attachment.content_type)
    except images.ImageRejected as exc:
        storage.delete(source)
        attachment.status = AttachmentStatus.REJECTED
        attachment.rejection_reason = str(exc)[:200]
        audit.record(
            "maintenance.attachment_rejected",
            "maintenance_request",
            request_id,
            organization_id=context.organization_id,
            details={"attachment_id": str(attachment.id), "reason": attachment.rejection_reason},
        )
        db.session.commit()
        raise RequestValidationError(str(exc), details={"json": {"file": [str(exc)]}}) from exc

    destination = final_key(attachment)
    storage.write(destination, processed, "image/jpeg")
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
        request_id,
        organization_id=context.organization_id,
        details={"attachment_id": str(attachment.id)},
    )
    db.session.commit()
    return attachment_view(attachment)


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
