"""Data access for maintenance requests.

Visibility rules (object-level authorization), in one place:
- owner: every request in the organization
- manager: requests in their assigned properties
- tenant: only requests they reported themselves
- contractor: requests behind work orders assigned to their contractor record
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, false, select

from app.auth.models import User
from app.authz.context import OrgContext
from app.contractors.models import Contractor
from app.extensions import db
from app.maintenance.models import MaintenanceComment, MaintenanceRequest, MaintenanceStatusHistory
from app.organizations.models import MembershipRole, OrganizationMembership
from app.properties.models import Property, Unit
from app.properties.repository import assigned_property_ids
from app.work_orders.models import CONTRACTOR_VISIBLE_STATUSES, WorkOrder

RequestRow = tuple[MaintenanceRequest, Property, Unit | None, User]
RequestSelect = Select[MaintenanceRequest, Property, Unit, User]
CommentRow = tuple[MaintenanceComment, OrganizationMembership, User]
MAX_HISTORY_ROWS = 200


def _request_rows(organization_id: uuid.UUID) -> RequestSelect:
    return (
        select(MaintenanceRequest, Property, Unit, User)
        .join(Property, Property.id == MaintenanceRequest.property_id)
        .outerjoin(Unit, Unit.id == MaintenanceRequest.unit_id)
        .join(
            OrganizationMembership,
            OrganizationMembership.id == MaintenanceRequest.reported_by_membership_id,
        )
        .join(User, User.id == OrganizationMembership.user_id)
        .where(MaintenanceRequest.organization_id == organization_id)
    )


def _contractor_request_ids(context: OrgContext) -> Select[uuid.UUID]:
    return (
        select(WorkOrder.request_id)
        .join(Contractor, Contractor.id == WorkOrder.contractor_id)
        .where(
            WorkOrder.organization_id == context.organization_id,
            Contractor.membership_id == context.membership_id,
            WorkOrder.status.in_(CONTRACTOR_VISIBLE_STATUSES),
        )
    )


def visible_requests(context: OrgContext) -> RequestSelect:
    stmt = _request_rows(context.organization_id)
    if context.role == MembershipRole.OWNER:
        return stmt
    if context.role == MembershipRole.MANAGER:
        return stmt.where(MaintenanceRequest.property_id.in_(assigned_property_ids(context)))
    if context.role == MembershipRole.TENANT:
        return stmt.where(MaintenanceRequest.reported_by_membership_id == context.membership_id)
    if context.role == MembershipRole.CONTRACTOR:
        return stmt.where(MaintenanceRequest.id.in_(_contractor_request_ids(context)))
    return stmt.where(false())


def get_visible_request(context: OrgContext, request_id: uuid.UUID) -> RequestRow | None:
    row = db.session.execute(
        visible_requests(context).where(MaintenanceRequest.id == request_id)
    ).first()
    return (row[0], row[1], row[2], row[3]) if row is not None else None


def history_rows(
    organization_id: uuid.UUID, request_id: uuid.UUID
) -> list[tuple[MaintenanceStatusHistory, User]]:
    stmt = (
        select(MaintenanceStatusHistory, User)
        .join(
            OrganizationMembership,
            OrganizationMembership.id == MaintenanceStatusHistory.changed_by_membership_id,
        )
        .join(User, User.id == OrganizationMembership.user_id)
        .where(
            MaintenanceStatusHistory.organization_id == organization_id,
            MaintenanceStatusHistory.request_id == request_id,
        )
        .order_by(MaintenanceStatusHistory.created_at, MaintenanceStatusHistory.id)
        .limit(MAX_HISTORY_ROWS)
    )
    return [(entry, user) for entry, user in db.session.execute(stmt)]


def comments_query(
    organization_id: uuid.UUID, request_id: uuid.UUID
) -> Select[MaintenanceComment, OrganizationMembership, User]:
    return (
        select(MaintenanceComment, OrganizationMembership, User)
        .join(
            OrganizationMembership,
            OrganizationMembership.id == MaintenanceComment.author_membership_id,
        )
        .join(User, User.id == OrganizationMembership.user_id)
        .where(
            MaintenanceComment.organization_id == organization_id,
            MaintenanceComment.request_id == request_id,
        )
    )


def get_comment_row(organization_id: uuid.UUID, comment_id: uuid.UUID) -> CommentRow | None:
    stmt = (
        select(MaintenanceComment, OrganizationMembership, User)
        .join(
            OrganizationMembership,
            OrganizationMembership.id == MaintenanceComment.author_membership_id,
        )
        .join(User, User.id == OrganizationMembership.user_id)
        .where(
            MaintenanceComment.organization_id == organization_id,
            MaintenanceComment.id == comment_id,
        )
    )
    row = db.session.execute(stmt).first()
    return (row[0], row[1], row[2]) if row is not None else None
