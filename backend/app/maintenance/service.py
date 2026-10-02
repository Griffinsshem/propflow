"""Maintenance request use cases (spec 3.4-3.6). One transaction each."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

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
from app.common.pagination import paginate
from app.extensions import db
from app.maintenance import repository, workflow
from app.maintenance.models import (
    MaintenanceComment,
    MaintenanceRequest,
    MaintenanceStatus,
    MaintenanceStatusHistory,
)
from app.maintenance.repository import CommentRow, RequestRow
from app.organizations.models import MembershipRole
from app.properties import repository as properties_repository
from app.properties.models import Unit
from app.tenants import repository as tenants_repository

STALE = "This request was changed by someone else. Reload it and try again."
TEXT_FIELDS = ("title", "description", "access_notes")
CHOICE_FIELDS = ("category", "priority")


def _now() -> datetime:
    return datetime.now(UTC)


def _text(value: str | None) -> str | None:
    return (value or "").strip() or None


def request_view(row: RequestRow, context: OrgContext | None = None) -> dict[str, Any]:
    request, prop, unit, reporter = row
    view: dict[str, Any] = {
        "id": request.id,
        "title": request.title,
        "description": request.description,
        "category": request.category,
        "priority": request.priority,
        "status": request.status,
        "access_notes": request.access_notes,
        "property": {"id": prop.id, "name": prop.name},
        "unit": {"id": unit.id, "label": unit.label} if unit is not None else None,
        "reported_by": {
            "membership_id": request.reported_by_membership_id,
            "full_name": reporter.full_name,
        },
        "version": request.version,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "resolved_at": request.resolved_at,
        "closed_at": request.closed_at,
    }
    if context is not None:
        view["allowed_transitions"] = workflow.allowed_next(request.status, context.role)
    return view


def comment_view(row: CommentRow) -> dict[str, Any]:
    comment, membership, user = row
    return {
        "id": comment.id,
        "body": comment.body,
        "author": {
            "membership_id": membership.id,
            "full_name": user.full_name,
            "role": membership.role,
        },
        "created_at": comment.created_at,
    }


def _record_status(
    request: MaintenanceRequest,
    from_status: str | None,
    to_status: str,
    context: OrgContext,
    reason: str | None,
) -> None:
    db.session.add(
        MaintenanceStatusHistory(
            organization_id=request.organization_id,
            request_id=request.id,
            from_status=from_status,
            to_status=to_status,
            changed_by_membership_id=context.membership_id,
            reason=reason,
        )
    )


def _location_for(context: OrgContext, data: dict[str, Any]) -> tuple[uuid.UUID, uuid.UUID | None]:
    """Returns (property_id, unit_id). Tenants never choose: their unit is looked up."""
    unit_id, property_id = data.get("unit_id"), data.get("property_id")
    if context.role == MembershipRole.TENANT:
        if unit_id is not None or property_id is not None:
            raise RequestValidationError(
                "Tenants report issues for their own unit.",
                details={"json": {"unit_id": ["Not allowed for tenants."]}},
            )
        profile = tenants_repository.get_profile_by_membership(
            context.organization_id, context.membership_id
        )
        unit = db.session.get(Unit, profile.unit_id) if profile and profile.unit_id else None
        if unit is None:
            raise ConflictError("You are not placed in a unit yet. Contact your property manager.")
        return unit.property_id, unit.id
    if unit_id is not None:
        visible_unit = properties_repository.get_visible_unit(context, unit_id)
        if visible_unit is None:
            raise NotFoundError()
        return visible_unit.property_id, visible_unit.id
    if property_id is not None:
        if properties_repository.get_visible_property(context, property_id) is None:
            raise NotFoundError()
        return property_id, None
    raise RequestValidationError(
        "Provide unit_id or property_id.",
        details={"json": {"unit_id": ["Required when property_id is not given."]}},
    )


def _visible_row(context: OrgContext, request_id: uuid.UUID) -> RequestRow:
    row = repository.get_visible_request(context, request_id)
    if row is None:
        raise NotFoundError()
    return row


def _commit() -> None:
    try:
        db.session.commit()
    except StaleDataError as exc:  # concurrent change between our read and write
        db.session.rollback()
        raise ConflictError(STALE) from exc


def create_request(context: OrgContext, data: dict[str, Any]) -> dict[str, Any]:
    property_id, unit_id = _location_for(context, data)
    request = MaintenanceRequest(
        organization_id=context.organization_id,
        property_id=property_id,
        unit_id=unit_id,
        reported_by_membership_id=context.membership_id,
        category=data["category"],
        priority=data["priority"],
        status=MaintenanceStatus.SUBMITTED,
        title=data["title"].strip(),
        description=data["description"].strip(),
        access_notes=_text(data.get("access_notes")),
    )
    db.session.add(request)
    db.session.flush()
    _record_status(request, None, MaintenanceStatus.SUBMITTED, context, None)
    audit.record(
        "maintenance.created",
        "maintenance_request",
        request.id,
        organization_id=context.organization_id,
        details={"category": request.category, "priority": request.priority},
    )
    db.session.commit()
    return get_request(context, request.id)


def list_requests(
    context: OrgContext,
    *,
    status: str | None,
    priority: str | None,
    property_id: uuid.UUID | None,
    unit_id: uuid.UUID | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    stmt = repository.visible_requests(context)
    if status is not None:
        stmt = stmt.where(MaintenanceRequest.status == status)
    if priority is not None:
        stmt = stmt.where(MaintenanceRequest.priority == priority)
    if property_id is not None:
        stmt = stmt.where(MaintenanceRequest.property_id == property_id)
    if unit_id is not None:
        stmt = stmt.where(MaintenanceRequest.unit_id == unit_id)
    rows, next_cursor = paginate(
        stmt,
        created_column=MaintenanceRequest.created_at,
        id_column=MaintenanceRequest.id,
        limit=limit,
        cursor=cursor,
        scalars=False,
    )
    return [request_view(tuple(row)) for row in rows], next_cursor


def get_request(context: OrgContext, request_id: uuid.UUID) -> dict[str, Any]:
    return request_view(_visible_row(context, request_id), context)


def update_request(
    context: OrgContext, request_id: uuid.UUID, data: dict[str, Any]
) -> dict[str, Any]:
    request = _visible_row(context, request_id)[0]
    if request.status == MaintenanceStatus.CLOSED:
        raise ConflictError("Closed requests cannot be edited.")
    if request.version != data.pop("version"):
        raise ConflictError(STALE)
    diff: dict[str, Any] = {}
    for field in CHOICE_FIELDS:
        if field in data and data[field] != getattr(request, field):
            diff[field] = {"from": getattr(request, field), "to": data[field]}
            setattr(request, field, data[field])
    for field in TEXT_FIELDS:
        if field in data:
            value = _text(data[field])
            if value != getattr(request, field):
                diff[field] = "changed"  # free text stays out of the audit trail
                setattr(request, field, value)
    if diff:
        audit.record(
            "maintenance.updated",
            "maintenance_request",
            request.id,
            organization_id=context.organization_id,
            details=diff,
        )
    _commit()
    return get_request(context, request_id)


def change_status(
    context: OrgContext,
    request_id: uuid.UUID,
    *,
    to_status: str,
    reason: str | None,
    version: int,
) -> dict[str, Any]:
    request = _visible_row(context, request_id)[0]
    if request.version != version:
        raise ConflictError(STALE)
    transition = workflow.get_transition(request.status, to_status)
    if transition is None:
        raise workflow.InvalidStatusTransitionError(
            f"A {request.status} request cannot move to {to_status}."
        )
    if not has_permission(context.role, transition.permission):
        raise PermissionDeniedError()
    reason = _text(reason)
    if transition.reason_required and reason is None:
        raise RequestValidationError(
            "A reason is required for this status change.",
            details={"json": {"reason": ["Required for this status change."]}},
        )

    previous = request.status
    request.status = to_status
    now = _now()
    if to_status == MaintenanceStatus.RESOLVED:
        request.resolved_at = now
    if previous == MaintenanceStatus.RESOLVED and to_status == MaintenanceStatus.IN_PROGRESS:
        request.resolved_at = None  # reopened
    if to_status == MaintenanceStatus.CLOSED:
        request.closed_at = now
    _record_status(request, previous, to_status, context, reason)
    audit.record(
        "maintenance.status_changed",
        "maintenance_request",
        request.id,
        organization_id=context.organization_id,
        details={"from": previous, "to": to_status},
    )
    _commit()
    return get_request(context, request_id)


def list_history(context: OrgContext, request_id: uuid.UUID) -> list[dict[str, Any]]:
    _visible_row(context, request_id)
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
        for entry, user in repository.history_rows(context.organization_id, request_id)
    ]


def add_comment(context: OrgContext, request_id: uuid.UUID, body: str) -> dict[str, Any]:
    request = _visible_row(context, request_id)[0]
    if request.status == MaintenanceStatus.CLOSED:
        raise ConflictError("Closed requests cannot receive new comments.")
    comment = MaintenanceComment(
        organization_id=context.organization_id,
        request_id=request.id,
        author_membership_id=context.membership_id,
        body=body.strip(),
    )
    db.session.add(comment)
    db.session.flush()
    audit.record(
        "maintenance.commented",
        "maintenance_request",
        request.id,
        organization_id=context.organization_id,
        details={"comment_id": str(comment.id)},
    )
    db.session.commit()
    row = repository.get_comment_row(context.organization_id, comment.id)
    if row is None:
        raise NotFoundError()
    return comment_view(row)


def list_comments(
    context: OrgContext, request_id: uuid.UUID, *, limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    _visible_row(context, request_id)
    rows, next_cursor = paginate(
        repository.comments_query(context.organization_id, request_id),
        created_column=MaintenanceComment.created_at,
        id_column=MaintenanceComment.id,
        limit=limit,
        cursor=cursor,
        scalars=False,
        newest_first=False,  # a conversation reads oldest first
    )
    return [comment_view(tuple(row)) for row in rows], next_cursor
