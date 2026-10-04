"""The caller's own in-app notifications in the active organization (every role)."""

from __future__ import annotations

import uuid
from typing import Any

from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.notifications import service
from app.notifications.schemas import (
    MarkedCountSchema,
    NotificationListQuerySchema,
    NotificationPageSchema,
    NotificationSchema,
    UnreadCountSchema,
)

blp = Blueprint(
    "notifications", __name__, url_prefix="/api/v1/notifications", description="Notifications."
)


@blp.get("")
@blp.arguments(NotificationListQuerySchema, location="query")
@blp.response(200, NotificationPageSchema)
@require_permission(Permission.ORGANIZATION_READ)
def list_notifications(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = service.list_notifications(
        current_org_context(),
        unread_only=query["unread_only"],
        limit=query["limit"],
        cursor=query["cursor"],
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.get("/unread-count")
@blp.response(200, UnreadCountSchema)
@require_permission(Permission.ORGANIZATION_READ)
def unread_count() -> dict[str, int]:
    return {"unread": service.unread_count(current_org_context())}


@blp.post("/<uuid:notification_id>/read")
@blp.response(200, NotificationSchema)
@require_permission(Permission.ORGANIZATION_READ)
def mark_read(notification_id: uuid.UUID) -> dict[str, Any]:
    return service.mark_read(current_org_context(), notification_id)


@blp.post("/read-all")
@blp.response(200, MarkedCountSchema)
@require_permission(Permission.ORGANIZATION_READ)
def mark_all_read() -> dict[str, int]:
    return {"updated": service.mark_all_read(current_org_context())}
