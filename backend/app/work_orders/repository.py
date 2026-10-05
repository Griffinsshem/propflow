"""Data access for work orders.

Visibility rules (object-level authorization), in one place:
- owner: every work order in the organization
- manager: work orders on requests in their assigned properties
- contractor: work orders assigned to their own contractor record (declined/cancelled hidden)
- tenant: none
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, Select, and_, false, select

from app.auth.models import User
from app.authz.context import OrgContext
from app.contractors.models import Contractor
from app.extensions import db
from app.maintenance.models import MaintenanceRequest
from app.organizations.models import MembershipRole, OrganizationMembership
from app.properties.models import Property, Unit
from app.properties.repository import assigned_property_ids
from app.work_orders.models import CONTRACTOR_VISIBLE_STATUSES, WorkOrder, WorkOrderStatusHistory

WorkOrderRow = tuple[WorkOrder, Contractor, MaintenanceRequest, Property, Unit | None]
WorkOrderSelect = Select[WorkOrder, Contractor, MaintenanceRequest, Property, Unit]
MAX_HISTORY_ROWS = 200


def _rows(organization_id: uuid.UUID) -> WorkOrderSelect:
    return (
        select(WorkOrder, Contractor, MaintenanceRequest, Property, Unit)
        .join(Contractor, Contractor.id == WorkOrder.contractor_id)
        .join(MaintenanceRequest, MaintenanceRequest.id == WorkOrder.request_id)
        .join(Property, Property.id == MaintenanceRequest.property_id)
        .outerjoin(Unit, Unit.id == MaintenanceRequest.unit_id)
        .where(WorkOrder.organization_id == organization_id)
    )


def _scope_condition(context: OrgContext) -> ColumnElement[bool]:
    """The visibility rule itself: one condition on work_orders (subqueries, no joins)."""
    in_org = WorkOrder.organization_id == context.organization_id
    if context.role == MembershipRole.OWNER:
        return in_org
    if context.role == MembershipRole.MANAGER:
        requests_in_scope = select(MaintenanceRequest.id).where(
            MaintenanceRequest.organization_id == context.organization_id,
            MaintenanceRequest.property_id.in_(assigned_property_ids(context)),
        )
        return and_(in_org, WorkOrder.request_id.in_(requests_in_scope))
    if context.role == MembershipRole.CONTRACTOR:
        own_records = select(Contractor.id).where(
            Contractor.organization_id == context.organization_id,
            Contractor.membership_id == context.membership_id,
        )
        return and_(
            in_org,
            WorkOrder.contractor_id.in_(own_records),
            WorkOrder.status.in_(CONTRACTOR_VISIBLE_STATUSES),
        )
    return false()


def visible_work_orders(context: OrgContext) -> WorkOrderSelect:
    """Visible work orders with display joins (contractor, request, location)."""
    return _rows(context.organization_id).where(_scope_condition(context))


def scoped_work_orders(context: OrgContext) -> Select[WorkOrder]:
    """The same visibility without display joins: counts and aggregates."""
    return select(WorkOrder).where(_scope_condition(context))


def _first(stmt: WorkOrderSelect) -> WorkOrderRow | None:
    row = db.session.execute(stmt).first()
    return (row[0], row[1], row[2], row[3], row[4]) if row is not None else None


def get_visible_work_order(context: OrgContext, work_order_id: uuid.UUID) -> WorkOrderRow | None:
    return _first(visible_work_orders(context).where(WorkOrder.id == work_order_id))


def get_work_order_row(organization_id: uuid.UUID, work_order_id: uuid.UUID) -> WorkOrderRow | None:
    """Unscoped within the org: only for re-reading a row the caller was just allowed to change."""
    return _first(_rows(organization_id).where(WorkOrder.id == work_order_id))


def history_rows(
    organization_id: uuid.UUID, work_order_id: uuid.UUID
) -> list[tuple[WorkOrderStatusHistory, User]]:
    stmt = (
        select(WorkOrderStatusHistory, User)
        .join(
            OrganizationMembership,
            OrganizationMembership.id == WorkOrderStatusHistory.changed_by_membership_id,
        )
        .join(User, User.id == OrganizationMembership.user_id)
        .where(
            WorkOrderStatusHistory.organization_id == organization_id,
            WorkOrderStatusHistory.work_order_id == work_order_id,
        )
        .order_by(WorkOrderStatusHistory.created_at, WorkOrderStatusHistory.id)
        .limit(MAX_HISTORY_ROWS)
    )
    return [(entry, user) for entry, user in db.session.execute(stmt)]


def work_order_rows(organization_id: uuid.UUID, ids: Sequence[uuid.UUID]) -> list[WorkOrderRow]:
    """Display rows for IDs already chosen through scoped_work_orders, in the given order."""
    if not ids:
        return []
    stmt = _rows(organization_id).where(WorkOrder.id.in_(ids))
    by_id = {
        row[0].id: (row[0], row[1], row[2], row[3], row[4]) for row in db.session.execute(stmt)
    }
    return [by_id[row_id] for row_id in ids if row_id in by_id]
