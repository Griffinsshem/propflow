"""Work order use cases (spec 3.9). One transaction each.

Work order status changes drive the linked maintenance request through
maintenance.service.apply_linked_status, so the two workflows can never disagree.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.audit import service as audit
from app.authz.context import OrgContext
from app.authz.permissions import has_permission
from app.common.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RequestValidationError,
)
from app.common.pagination import paginate_keys
from app.contractors import repository as contractors_repository
from app.contractors.models import Contractor, ContractorStatus
from app.extensions import db
from app.maintenance import repository as maintenance_repository
from app.maintenance import service as maintenance_service
from app.maintenance.models import MaintenanceStatus
from app.maintenance.workflow import InvalidStatusTransitionError
from app.notifications import service as notifications
from app.work_orders import repository, workflow
from app.work_orders.models import (
    ACTIVE_STATUSES,
    WorkOrder,
    WorkOrderStatus,
    WorkOrderStatusHistory,
)
from app.work_orders.repository import WorkOrderRow

STALE = "This work order was changed by someone else. Reload it and try again."
ONE_ACTIVE = "This request already has an active work order."
ASSIGNABLE_REQUEST_STATUSES = frozenset({MaintenanceStatus.TRIAGED, MaintenanceStatus.ASSIGNED})
REASSIGNABLE_STATUSES = frozenset({WorkOrderStatus.ASSIGNED, WorkOrderStatus.DECLINED})


def _today() -> date:
    return datetime.now(UTC).date()


def _text(value: str | None) -> str | None:
    return (value or "").strip() or None


def work_order_view(row: WorkOrderRow, context: OrgContext | None = None) -> dict[str, Any]:
    order, contractor, request, prop, unit = row
    view: dict[str, Any] = {
        "id": order.id,
        "status": order.status,
        "priority": order.priority,
        "description": order.description,
        "due_date": order.due_date,
        "is_overdue": order.due_date is not None
        and order.status in ACTIVE_STATUSES
        and order.due_date < _today(),
        "completed_at": order.completed_at,
        "version": order.version,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "contractor": {
            "id": contractor.id,
            "business_name": contractor.business_name,
            "specialty": contractor.specialty,
        },
        "request": {
            "id": request.id,
            "title": request.title,
            "description": request.description,
            "category": request.category,
            "status": request.status,
            "access_notes": request.access_notes,
        },
        "location": {
            "property_id": prop.id,
            "property_name": prop.name,
            "address_line": prop.address_line,
            "city": prop.city,
            "unit_id": unit.id if unit is not None else None,
            "unit_label": unit.label if unit is not None else None,
        },
    }
    if context is not None:
        view["allowed_transitions"] = workflow.allowed_next(order.status, context.role)
    return view


def _visible_row(context: OrgContext, work_order_id: uuid.UUID) -> WorkOrderRow:
    row = repository.get_visible_work_order(context, work_order_id)
    if row is None:
        raise NotFoundError()
    return row


def _reload(context: OrgContext, work_order_id: uuid.UUID) -> dict[str, Any]:
    row = repository.get_work_order_row(context.organization_id, work_order_id)
    if row is None:
        raise NotFoundError()
    return work_order_view(row, context)


def _active_contractor(context: OrgContext, contractor_id: uuid.UUID) -> Contractor:
    contractor = contractors_repository.get_contractor(context.organization_id, contractor_id)
    if contractor is None:
        raise NotFoundError()
    if contractor.status != ContractorStatus.ACTIVE:
        raise RequestValidationError(
            "This contractor is inactive.",
            details={"json": {"contractor_id": ["Contractor is inactive."]}},
        )
    return contractor


def _record(
    order: WorkOrder,
    from_status: str | None,
    to_status: str,
    context: OrgContext,
    reason: str | None,
) -> None:
    db.session.add(
        WorkOrderStatusHistory(
            organization_id=order.organization_id,
            work_order_id=order.id,
            from_status=from_status,
            to_status=to_status,
            changed_by_membership_id=context.membership_id,
            reason=reason,
        )
    )


def _commit() -> None:
    try:
        db.session.commit()
    except StaleDataError as exc:
        db.session.rollback()
        raise ConflictError(STALE) from exc
    except IntegrityError as exc:  # the partial unique index: one active order per request
        db.session.rollback()
        raise ConflictError(ONE_ACTIVE) from exc


def list_work_orders(
    context: OrgContext,
    *,
    status: str | None,
    contractor_id: uuid.UUID | None,
    request_id: uuid.UUID | None,
    overdue: bool,
    limit: int,
    cursor: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    # Choose the page from the join-free scope, then join display data for that page only.
    stmt = repository.scoped_work_orders(context)
    if status is not None:
        stmt = stmt.where(WorkOrder.status == status)
    if contractor_id is not None:
        stmt = stmt.where(WorkOrder.contractor_id == contractor_id)
    if request_id is not None:
        stmt = stmt.where(WorkOrder.request_id == request_id)
    if overdue:
        stmt = stmt.where(WorkOrder.due_date < _today(), WorkOrder.status.in_(ACTIVE_STATUSES))
    ids, next_cursor = paginate_keys(
        stmt,
        created_column=WorkOrder.created_at,
        id_column=WorkOrder.id,
        limit=limit,
        cursor=cursor,
    )
    rows = repository.work_order_rows(context.organization_id, ids)
    return [work_order_view(row) for row in rows], next_cursor


def get_work_order(context: OrgContext, work_order_id: uuid.UUID) -> dict[str, Any]:
    return work_order_view(_visible_row(context, work_order_id), context)


def create_work_order(context: OrgContext, data: dict[str, Any]) -> dict[str, Any]:
    request_row = maintenance_repository.get_visible_request(context, data["request_id"])
    if request_row is None:
        raise NotFoundError()
    request = request_row[0]
    if request.status not in ASSIGNABLE_REQUEST_STATUSES:
        raise ConflictError("Only triaged requests can be turned into work orders.")
    contractor = _active_contractor(context, data["contractor_id"])
    order = WorkOrder(
        organization_id=context.organization_id,
        request_id=request.id,
        contractor_id=contractor.id,
        created_by_membership_id=context.membership_id,
        status=WorkOrderStatus.ASSIGNED,
        priority=data.get("priority") or request.priority,
        description=_text(data.get("description")),
        due_date=data.get("due_date"),
    )
    db.session.add(order)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError(ONE_ACTIVE) from exc
    _record(order, None, WorkOrderStatus.ASSIGNED, context, None)
    maintenance_service.apply_linked_status(request, MaintenanceStatus.ASSIGNED, context, None)
    audit.record(
        "work_order.created",
        "work_order",
        order.id,
        organization_id=context.organization_id,
        details={"request_id": str(request.id), "contractor_id": str(contractor.id)},
    )
    notifications.notify_work_order_assigned(context, order, request)
    db.session.commit()
    return _reload(context, order.id)


def update_work_order(
    context: OrgContext, work_order_id: uuid.UUID, data: dict[str, Any]
) -> dict[str, Any]:
    order = _visible_row(context, work_order_id)[0]
    if order.status not in ACTIVE_STATUSES:
        raise ConflictError("Only active work orders can be edited.")
    if order.version != data.pop("version"):
        raise ConflictError(STALE)
    diff: dict[str, Any] = {}
    if "priority" in data and data["priority"] != order.priority:
        diff["priority"] = {"from": order.priority, "to": data["priority"]}
        order.priority = data["priority"]
    if "due_date" in data and data["due_date"] != order.due_date:
        diff["due_date"] = {
            "from": order.due_date.isoformat() if order.due_date else None,
            "to": data["due_date"].isoformat() if data["due_date"] else None,
        }
        order.due_date = data["due_date"]
    if "description" in data and _text(data["description"]) != order.description:
        diff["description"] = "changed"
        order.description = _text(data["description"])
    if diff:
        audit.record(
            "work_order.updated",
            "work_order",
            order.id,
            organization_id=context.organization_id,
            details=diff,
        )
    _commit()
    return _reload(context, work_order_id)


def assign_contractor(
    context: OrgContext, work_order_id: uuid.UUID, *, contractor_id: uuid.UUID, version: int
) -> dict[str, Any]:
    order, _, request, _, _ = _visible_row(context, work_order_id)
    if order.version != version:
        raise ConflictError(STALE)
    if order.status not in REASSIGNABLE_STATUSES:
        raise ConflictError("Only unaccepted or declined work orders can be reassigned.")
    contractor = _active_contractor(context, contractor_id)
    previous_contractor, previous_status = order.contractor_id, order.status
    if contractor.id == previous_contractor and previous_status == WorkOrderStatus.ASSIGNED:
        return _reload(context, work_order_id)
    order.contractor_id = contractor.id
    if previous_status == WorkOrderStatus.DECLINED:
        order.status = WorkOrderStatus.ASSIGNED
        _record(order, previous_status, WorkOrderStatus.ASSIGNED, context, "Reassigned")
        maintenance_service.apply_linked_status(request, MaintenanceStatus.ASSIGNED, context, None)
    audit.record(
        "work_order.assigned",
        "work_order",
        order.id,
        organization_id=context.organization_id,
        details={"from": str(previous_contractor), "to": str(contractor.id)},
    )
    notifications.notify_work_order_assigned(context, order, request)
    _commit()
    return _reload(context, work_order_id)


def change_status(
    context: OrgContext,
    work_order_id: uuid.UUID,
    *,
    to_status: str,
    reason: str | None,
    version: int,
) -> dict[str, Any]:
    order, _, request, _, _ = _visible_row(context, work_order_id)
    if order.version != version:
        raise ConflictError(STALE)
    transition = workflow.get_transition(order.status, to_status)
    if transition is None:
        raise InvalidStatusTransitionError(
            f"A {order.status} work order cannot move to {to_status}."
        )
    if not has_permission(context.role, transition.permission):
        raise PermissionDeniedError()
    reason = _text(reason)
    if transition.reason_required and reason is None:
        raise RequestValidationError(
            "A reason is required for this status change.",
            details={"json": {"reason": ["Required for this status change."]}},
        )
    previous = order.status
    order.status = to_status
    if to_status == WorkOrderStatus.COMPLETED:
        order.completed_at = datetime.now(UTC)
    _record(order, previous, to_status, context, reason)
    effect = workflow.REQUEST_EFFECTS.get(to_status)
    if effect is not None:
        maintenance_service.apply_linked_status(
            request, effect, context, reason or f"Work order {to_status}"
        )
    audit.record(
        "work_order.status_changed",
        "work_order",
        order.id,
        organization_id=context.organization_id,
        details={"from": previous, "to": to_status},
    )
    notifications.notify_work_order_status(context, order, request)
    _commit()
    return _reload(context, work_order_id)


def list_history(context: OrgContext, work_order_id: uuid.UUID) -> list[dict[str, Any]]:
    _visible_row(context, work_order_id)
    return [
        {
            "from_status": entry.from_status,
            "to_status": entry.to_status,
            "reason": entry.reason,
            "changed_by": {
                "membership_id": entry.changed_by_membership_id,
                "full_name": user.full_name,
            },
            "created_at": entry.created_at,
        }
        for entry, user in repository.history_rows(context.organization_id, work_order_id)
    ]
