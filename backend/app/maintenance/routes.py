"""Maintenance endpoints: a thin HTTP layer over app.maintenance.service.

MAINTENANCE_READ is the baseline for status changes; the workflow then requires the
specific permission each transition names.
"""

from __future__ import annotations

import uuid
from typing import Any

from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.common.pagination import PageQuerySchema
from app.common.rate_limit import client_key, limiter
from app.maintenance import service
from app.maintenance.schemas import (
    CommentCreateSchema,
    CommentPageSchema,
    CommentSchema,
    MaintenanceCreateSchema,
    MaintenanceListQuerySchema,
    MaintenancePageSchema,
    MaintenanceRequestSchema,
    MaintenanceStatusChangeSchema,
    MaintenanceUpdateSchema,
    StatusHistorySchema,
)

blp = Blueprint(
    "maintenance", __name__, url_prefix="/api/v1/maintenance", description="Maintenance requests."
)


@blp.get("")
@blp.arguments(MaintenanceListQuerySchema, location="query")
@blp.response(200, MaintenancePageSchema)
@require_permission(Permission.MAINTENANCE_READ)
def list_requests(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = service.list_requests(
        current_org_context(),
        status=query["status"],
        priority=query["priority"],
        property_id=query["property_id"],
        unit_id=query["unit_id"],
        limit=query["limit"],
        cursor=query["cursor"],
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.post("")
@limiter.limit("20 per hour", key_func=client_key)
@blp.arguments(MaintenanceCreateSchema)
@blp.response(201, MaintenanceRequestSchema)
@require_permission(Permission.MAINTENANCE_CREATE)
def create_request(payload: dict[str, Any]) -> dict[str, Any]:
    return service.create_request(current_org_context(), payload)


@blp.get("/<uuid:request_id>")
@blp.response(200, MaintenanceRequestSchema)
@require_permission(Permission.MAINTENANCE_READ)
def get_request(request_id: uuid.UUID) -> dict[str, Any]:
    return service.get_request(current_org_context(), request_id)


@blp.patch("/<uuid:request_id>")
@blp.arguments(MaintenanceUpdateSchema)
@blp.response(200, MaintenanceRequestSchema)
@require_permission(Permission.MAINTENANCE_UPDATE)
def update_request(payload: dict[str, Any], request_id: uuid.UUID) -> dict[str, Any]:
    return service.update_request(current_org_context(), request_id, payload)


@blp.post("/<uuid:request_id>/status")
@blp.arguments(MaintenanceStatusChangeSchema)
@blp.response(200, MaintenanceRequestSchema)
@require_permission(Permission.MAINTENANCE_READ)
def change_status(payload: dict[str, Any], request_id: uuid.UUID) -> dict[str, Any]:
    return service.change_status(
        current_org_context(),
        request_id,
        to_status=payload["status"],
        reason=payload["reason"],
        version=payload["version"],
    )


@blp.get("/<uuid:request_id>/history")
@blp.response(200, StatusHistorySchema(many=True))
@require_permission(Permission.MAINTENANCE_READ)
def list_history(request_id: uuid.UUID) -> list[dict[str, Any]]:
    return service.list_history(current_org_context(), request_id)


@blp.get("/<uuid:request_id>/comments")
@blp.arguments(PageQuerySchema, location="query")
@blp.response(200, CommentPageSchema)
@require_permission(Permission.MAINTENANCE_READ)
def list_comments(query: dict[str, Any], request_id: uuid.UUID) -> dict[str, Any]:
    items, next_cursor = service.list_comments(
        current_org_context(), request_id, limit=query["limit"], cursor=query["cursor"]
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.post("/<uuid:request_id>/comments")
@limiter.limit("60 per hour", key_func=client_key)
@blp.arguments(CommentCreateSchema)
@blp.response(201, CommentSchema)
@require_permission(Permission.MAINTENANCE_COMMENT)
def add_comment(payload: dict[str, Any], request_id: uuid.UUID) -> dict[str, Any]:
    return service.add_comment(current_org_context(), request_id, payload["body"])
