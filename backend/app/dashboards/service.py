"""Dashboards (spec 3.10-3.12): real data only, computed in a few aggregate queries.

Every number is an aggregate over the same scoped query the matching list page uses, so a
dashboard can never count a record its viewer could not open. Counters use
COUNT(*) FILTER (WHERE ...) so each block is one query regardless of data volume.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.audit import service as audit_service
from app.authz.context import OrgContext
from app.common.errors import NotFoundError
from app.extensions import db
from app.maintenance import repository as maintenance_repository
from app.maintenance import service as maintenance_service
from app.maintenance.models import MaintenancePriority, MaintenanceRequest
from app.maintenance.models import MaintenanceStatus as S
from app.notifications import service as notifications_service
from app.organizations.models import MembershipRole, MembershipStatus, OrganizationMembership
from app.properties import repository as properties_repository
from app.properties.models import Property, PropertyStatus, Unit
from app.tenants import repository as tenants_repository
from app.tenants import service as tenants_service
from app.work_orders import repository as work_orders_repository
from app.work_orders import service as work_orders_service
from app.work_orders.models import ACTIVE_STATUSES, WorkOrder
from app.work_orders.models import WorkOrderStatus as W

RECENT_LIMIT = 5
UPCOMING_LIMIT = 10
ACTIVITY_LIMIT = 10
OPEN = (S.SUBMITTED, S.TRIAGED, S.ASSIGNED, S.IN_PROGRESS, S.WAITING)
IN_FLIGHT = (S.TRIAGED, S.ASSIGNED, S.IN_PROGRESS, S.WAITING)


def _now() -> datetime:
    return datetime.now(UTC)


def _month_start() -> datetime:
    return _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _as_counts(row: Any) -> dict[str, int]:
    return {key: int(value) for key, value in row._mapping.items()}


def _request_counts(
    context: OrgContext,
    *,
    property_id: uuid.UUID | None = None,
    reporter_id: uuid.UUID | None = None,
) -> dict[str, int]:
    scoped = maintenance_repository.scoped_requests(context).with_only_columns(
        MaintenanceRequest.status,
        MaintenanceRequest.priority,
        MaintenanceRequest.resolved_at,
    )
    if property_id is not None:
        scoped = scoped.where(MaintenanceRequest.property_id == property_id)
    if reporter_id is not None:
        scoped = scoped.where(MaintenanceRequest.reported_by_membership_id == reporter_id)
    sub = scoped.subquery()
    stmt = select(
        func.count().filter(sub.c.status.in_(OPEN)).label("open"),
        func.count().filter(sub.c.status == S.SUBMITTED).label("new"),
        func.count()
        .filter(sub.c.status.in_(OPEN), sub.c.priority == MaintenancePriority.URGENT)
        .label("urgent"),
        func.count().filter(sub.c.status.in_(IN_FLIGHT)).label("in_flight"),
        func.count().filter(sub.c.status == S.IN_PROGRESS).label("in_progress"),
        func.count().filter(sub.c.status == S.WAITING).label("waiting"),
        func.count().filter(sub.c.status == S.RESOLVED).label("resolved"),
        func.count().filter(sub.c.status == S.CLOSED).label("closed"),
        func.count().filter(sub.c.resolved_at >= _month_start()).label("resolved_this_month"),
    ).select_from(sub)
    return _as_counts(db.session.execute(stmt).one())


def _work_order_counts(
    context: OrgContext, *, property_id: uuid.UUID | None = None
) -> dict[str, int]:
    scoped = work_orders_repository.scoped_work_orders(context).with_only_columns(
        WorkOrder.status, WorkOrder.due_date, WorkOrder.completed_at
    )
    if property_id is not None:
        requests_on_property = select(MaintenanceRequest.id).where(
            MaintenanceRequest.organization_id == context.organization_id,
            MaintenanceRequest.property_id == property_id,
        )
        scoped = scoped.where(WorkOrder.request_id.in_(requests_on_property))
    sub = scoped.subquery()
    today = _now().date()
    stmt = select(
        func.count().filter(sub.c.status == W.ASSIGNED).label("awaiting_acceptance"),
        func.count().filter(sub.c.status == W.ACCEPTED).label("accepted"),
        func.count().filter(sub.c.status == W.IN_PROGRESS).label("in_progress"),
        func.count().filter(sub.c.status.in_(ACTIVE_STATUSES)).label("active"),
        func.count()
        .filter(sub.c.status.in_(ACTIVE_STATUSES), sub.c.due_date < today)
        .label("overdue"),
        func.count().filter(sub.c.completed_at >= _month_start()).label("completed_this_month"),
    ).select_from(sub)
    return _as_counts(db.session.execute(stmt).one())


def _ids(stmt: Any) -> list[uuid.UUID]:
    return list(db.session.execute(stmt).scalars())


def _request_views(context: OrgContext, ids: list[uuid.UUID]) -> list[dict[str, Any]]:
    rows = maintenance_repository.request_rows(context.organization_id, ids)
    return [maintenance_service.request_view(row) for row in rows]


def _work_order_views(context: OrgContext, ids: list[uuid.UUID]) -> list[dict[str, Any]]:
    rows = work_orders_repository.work_order_rows(context.organization_id, ids)
    return [work_orders_service.work_order_view(row) for row in rows]


def _recently_updated(context: OrgContext, property_id: uuid.UUID | None) -> list[dict[str, Any]]:
    stmt = maintenance_repository.scoped_requests(context).with_only_columns(MaintenanceRequest.id)
    if property_id is not None:
        stmt = stmt.where(MaintenanceRequest.property_id == property_id)
    stmt = stmt.order_by(MaintenanceRequest.updated_at.desc(), MaintenanceRequest.id.desc())
    return _request_views(context, _ids(stmt.limit(RECENT_LIMIT)))


def _overdue_work_orders(
    context: OrgContext, property_id: uuid.UUID | None
) -> list[dict[str, Any]]:
    stmt = (
        work_orders_repository.scoped_work_orders(context)
        .with_only_columns(WorkOrder.id)
        .where(WorkOrder.status.in_(ACTIVE_STATUSES), WorkOrder.due_date < _now().date())
    )
    if property_id is not None:
        requests_on_property = select(MaintenanceRequest.id).where(
            MaintenanceRequest.organization_id == context.organization_id,
            MaintenanceRequest.property_id == property_id,
        )
        stmt = stmt.where(WorkOrder.request_id.in_(requests_on_property))
    stmt = stmt.order_by(WorkOrder.due_date.asc(), WorkOrder.created_at.asc(), WorkOrder.id.asc())
    return _work_order_views(context, _ids(stmt.limit(RECENT_LIMIT)))


def operations(context: OrgContext, *, property_id: uuid.UUID | None) -> dict[str, Any]:
    """Owner and manager view: what needs attention, within the caller's visibility."""
    if property_id is not None and (
        properties_repository.get_visible_property(context, property_id) is None
    ):
        raise NotFoundError()
    recent, _ = maintenance_service.list_requests(
        context,
        status=None,
        priority=None,
        property_id=property_id,
        unit_id=None,
        limit=RECENT_LIMIT,
        cursor=None,
    )
    return {
        "requests": _request_counts(context, property_id=property_id),
        "work_orders": _work_order_counts(context, property_id=property_id),
        "recent_requests": recent,
        "recently_updated": _recently_updated(context, property_id),
        "overdue_work_orders": _overdue_work_orders(context, property_id),
    }


def organization(context: OrgContext) -> dict[str, Any]:
    """Owner view: organization-wide totals in one statement, plus recent audit activity."""
    org = context.organization_id
    stmt = select(
        select(func.count())
        .select_from(Property)
        .where(Property.organization_id == org, Property.status == PropertyStatus.ACTIVE)
        .scalar_subquery()
        .label("properties"),
        select(func.count())
        .select_from(Unit)
        .where(Unit.organization_id == org)
        .scalar_subquery()
        .label("units"),
        select(func.count())
        .select_from(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == org,
            OrganizationMembership.role == MembershipRole.TENANT,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
        )
        .scalar_subquery()
        .label("active_tenants"),
        select(func.count())
        .select_from(MaintenanceRequest)
        .where(MaintenanceRequest.organization_id == org, MaintenanceRequest.status.in_(OPEN))
        .scalar_subquery()
        .label("open_requests"),
        select(func.count())
        .select_from(WorkOrder)
        .where(WorkOrder.organization_id == org, WorkOrder.status.in_(ACTIVE_STATUSES))
        .scalar_subquery()
        .label("active_work_orders"),
    )
    activity, _ = audit_service.list_for_organization(org, limit=ACTIVITY_LIMIT, cursor=None)
    return {"counts": _as_counts(db.session.execute(stmt).one()), "recent_activity": activity}


def tenant(context: OrgContext) -> dict[str, Any]:
    """The caller's own unit, requests and recent activity."""
    own = tenants_repository.get_own_tenant(context)
    counts = _request_counts(context, reporter_id=context.membership_id)
    recent = (
        maintenance_repository.scoped_requests(context)
        .with_only_columns(MaintenanceRequest.id)
        .where(MaintenanceRequest.reported_by_membership_id == context.membership_id)
        .order_by(MaintenanceRequest.created_at.desc(), MaintenanceRequest.id.desc())
        .limit(RECENT_LIMIT)
    )
    activity, _ = notifications_service.list_notifications(
        context, unread_only=False, limit=RECENT_LIMIT, cursor=None
    )
    return {
        "unit": tenants_service.tenant_view(own)["unit"] if own is not None else None,
        "requests": {
            "submitted": counts["new"],
            "in_progress": counts["in_flight"],
            "waiting": counts["waiting"],
            "resolved": counts["resolved"],
            "closed": counts["closed"],
        },
        "recent_requests": _request_views(context, _ids(recent)),
        "recent_activity": activity,
    }


def contractor(context: OrgContext) -> dict[str, Any]:
    """The caller's work: counters and active jobs, soonest due first."""
    upcoming = (
        work_orders_repository.scoped_work_orders(context)
        .with_only_columns(WorkOrder.id)
        .where(WorkOrder.status.in_(ACTIVE_STATUSES))
        .order_by(
            WorkOrder.due_date.asc().nulls_last(), WorkOrder.created_at.asc(), WorkOrder.id.asc()
        )
        .limit(UPCOMING_LIMIT)
    )
    return {
        "work_orders": _work_order_counts(context),
        "upcoming": _work_order_views(context, _ids(upcoming)),
    }
