"""Attachment endpoints (same URL space as maintenance, separate blueprint)."""

from __future__ import annotations

import uuid
from typing import Any

from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.common.rate_limit import client_key, limiter
from app.maintenance import attachments
from app.maintenance.attachment_schemas import (
    AttachmentSchema,
    AttachmentUploadRequestSchema,
    AttachmentUploadSchema,
)

blp = Blueprint(
    "maintenance_attachments",
    __name__,
    url_prefix="/api/v1/maintenance",
    description="Photo attachments on maintenance requests.",
)


@blp.get("/<uuid:request_id>/attachments")
@blp.response(200, AttachmentSchema(many=True))
@require_permission(Permission.MAINTENANCE_READ)
def list_attachments(request_id: uuid.UUID) -> list[dict[str, Any]]:
    return attachments.list_attachments(current_org_context(), request_id)


@blp.post("/<uuid:request_id>/attachments")
@limiter.limit("30 per hour", key_func=client_key)
@blp.arguments(AttachmentUploadRequestSchema)
@blp.response(201, AttachmentUploadSchema)
@require_permission(Permission.MAINTENANCE_COMMENT)
def start_upload(payload: dict[str, Any], request_id: uuid.UUID) -> dict[str, Any]:
    return attachments.start_upload(
        current_org_context(),
        request_id,
        content_type=payload["content_type"],
        size_bytes=payload["size_bytes"],
    )


@blp.post("/<uuid:request_id>/attachments/<uuid:attachment_id>/complete")
@limiter.limit("60 per hour", key_func=client_key)
@blp.response(202, AttachmentSchema)
@require_permission(Permission.MAINTENANCE_COMMENT)
def complete_upload(request_id: uuid.UUID, attachment_id: uuid.UUID) -> dict[str, Any]:
    return attachments.complete_upload(current_org_context(), request_id, attachment_id)


@blp.get("/<uuid:request_id>/attachments/<uuid:attachment_id>")
@blp.response(200, AttachmentSchema)
@require_permission(Permission.MAINTENANCE_READ)
def get_attachment(request_id: uuid.UUID, attachment_id: uuid.UUID) -> dict[str, Any]:
    return attachments.get_attachment(current_org_context(), request_id, attachment_id)
