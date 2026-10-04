"""Work order endpoints. WORKORDER_READ is the baseline for status changes; the workflow
then requires the specific permission each transition names."""

from __future__ import annotations

import uuid
from typing import Any

from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.work_orders import service
from app.work_orders.schemas import (
    WorkOrderAssignSchema,
    WorkOrderCreateSchema,
    WorkOrderHistorySchema,
    WorkOrderListQuerySchema,
    WorkOrderPageSchema,
    WorkOrderSchema,
    WorkOrderStatusChangeSchema,
    WorkOrderUpdateSchema,
)

blp = Blueprint(
    "work_orders", __name__, url_prefix="/api/v1/work-orders", description="Work orders."
)


@blp.get("")
@blp.arguments(WorkOrderListQuerySchema, location="query")
@blp.response(200, WorkOrderPageSchema)
@require_permission(Permission.WORKORDER_READ)
def list_work_orders(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = service.list_work_orders(
        current_org_context(),
        status=query["status"],
        contractor_id=query["contractor_id"],
        request_id=query["request_id"],
        overdue=query["overdue"],
        limit=query["limit"],
        cursor=query["cursor"],
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.post("")
@blp.arguments(WorkOrderCreateSchema)
@blp.response(201, WorkOrderSchema)
@require_permission(Permission.WORKORDER_CREATE)
def create_work_order(payload: dict[str, Any]) -> dict[str, Any]:
    return service.create_work_order(current_org_context(), payload)


@blp.get("/<uuid:work_order_id>")
@blp.response(200, WorkOrderSchema)
@require_permission(Permission.WORKORDER_READ)
def get_work_order(work_order_id: uuid.UUID) -> dict[str, Any]:
    return service.get_work_order(current_org_context(), work_order_id)


@blp.patch("/<uuid:work_order_id>")
@blp.arguments(WorkOrderUpdateSchema)
@blp.response(200, WorkOrderSchema)
@require_permission(Permission.WORKORDER_ASSIGN)
def update_work_order(payload: dict[str, Any], work_order_id: uuid.UUID) -> dict[str, Any]:
    return service.update_work_order(current_org_context(), work_order_id, payload)


@blp.post("/<uuid:work_order_id>/assign")
@blp.arguments(WorkOrderAssignSchema)
@blp.response(200, WorkOrderSchema)
@require_permission(Permission.WORKORDER_ASSIGN)
def assign_contractor(payload: dict[str, Any], work_order_id: uuid.UUID) -> dict[str, Any]:
    return service.assign_contractor(
        current_org_context(),
        work_order_id,
        contractor_id=payload["contractor_id"],
        version=payload["version"],
    )


@blp.post("/<uuid:work_order_id>/status")
@blp.arguments(WorkOrderStatusChangeSchema)
@blp.response(200, WorkOrderSchema)
@require_permission(Permission.WORKORDER_READ)
def change_status(payload: dict[str, Any], work_order_id: uuid.UUID) -> dict[str, Any]:
    return service.change_status(
        current_org_context(),
        work_order_id,
        to_status=payload["status"],
        reason=payload["reason"],
        version=payload["version"],
    )


@blp.get("/<uuid:work_order_id>/history")
@blp.response(200, WorkOrderHistorySchema(many=True))
@require_permission(Permission.WORKORDER_READ)
def list_history(work_order_id: uuid.UUID) -> list[dict[str, Any]]:
    return service.list_history(current_org_context(), work_order_id)
