"""In-app notifications.

Rows are written in the same transaction as the event that causes them, so a notification
exists if and only if its event committed: nothing is duplicated on retry or lost when a
worker is down. Recipients are people who can already see the resource; the actor is never
notified of their own action. Bodies are short summaries, never comment text.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update

from app.authz.context import OrgContext
from app.common.errors import NotFoundError
from app.common.pagination import paginate
from app.contractors.models import Contractor
from app.extensions import db
from app.maintenance.models import MaintenanceRequest
from app.notifications.models import Notification, NotificationKind
from app.organizations.models import MembershipRole, MembershipStatus, OrganizationMembership
from app.properties.models import PropertyAssignment
from app.work_orders.models import ACTIVE_STATUSES, WorkOrder


def _label(status: str) -> str:
    return status.replace("_", " ")


# --- Recipients -----------------------------------------------------------------------------


def _responsible_staff(organization_id: uuid.UUID, property_id: uuid.UUID) -> set[uuid.UUID]:
    """The property's assigned managers; the owners when nobody is assigned."""
    managers = (
        select(OrganizationMembership.id)
        .join(PropertyAssignment, PropertyAssignment.membership_id == OrganizationMembership.id)
        .where(
            PropertyAssignment.organization_id == organization_id,
            PropertyAssignment.property_id == property_id,
            OrganizationMembership.role == MembershipRole.MANAGER,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    found = set(db.session.execute(managers).scalars())
    if found:
        return found
    owners = select(OrganizationMembership.id).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.role == MembershipRole.OWNER,
        OrganizationMembership.status == MembershipStatus.ACTIVE,
    )
    return set(db.session.execute(owners).scalars())


def _contractor_logins_on_request(
    organization_id: uuid.UUID, request_id: uuid.UUID
) -> set[uuid.UUID]:
    stmt = (
        select(Contractor.membership_id)
        .join(WorkOrder, WorkOrder.contractor_id == Contractor.id)
        .where(
            WorkOrder.organization_id == organization_id,
            WorkOrder.request_id == request_id,
            WorkOrder.status.in_(ACTIVE_STATUSES),
            Contractor.membership_id.is_not(None),
        )
    )
    return {member for member in db.session.execute(stmt).scalars() if member is not None}


def _contractor_login(organization_id: uuid.UUID, contractor_id: uuid.UUID) -> set[uuid.UUID]:
    stmt = select(Contractor.membership_id).where(
        Contractor.organization_id == organization_id, Contractor.id == contractor_id
    )
    member = db.session.execute(stmt).scalar_one_or_none()
    return {member} if member is not None else set()


def _add(
    context: OrgContext,
    recipients: Iterable[uuid.UUID],
    kind: NotificationKind,
    title: str,
    body: str,
    resource_type: str,
    resource_id: uuid.UUID,
) -> None:
    for membership_id in sorted(set(recipients) - {context.membership_id}):
        db.session.add(
            Notification(
                organization_id=context.organization_id,
                recipient_membership_id=membership_id,
                kind=kind,
                title=title,
                body=body[:500],
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )


# --- Event hooks (called inside the event's transaction) ---------------------------------


def notify_request_submitted(context: OrgContext, request: MaintenanceRequest) -> None:
    _add(
        context,
        _responsible_staff(context.organization_id, request.property_id),
        NotificationKind.REQUEST_SUBMITTED,
        "New maintenance request",
        request.title,
        "maintenance_request",
        request.id,
    )


def notify_request_status(context: OrgContext, request: MaintenanceRequest) -> None:
    _add(
        context,
        {request.reported_by_membership_id},
        NotificationKind.REQUEST_STATUS_CHANGED,
        "Maintenance request updated",
        f"{request.title} is now {_label(request.status)}.",
        "maintenance_request",
        request.id,
    )


def notify_request_comment(context: OrgContext, request: MaintenanceRequest) -> None:
    recipients = (
        {request.reported_by_membership_id}
        | _responsible_staff(context.organization_id, request.property_id)
        | _contractor_logins_on_request(context.organization_id, request.id)
    )
    _add(
        context,
        recipients,
        NotificationKind.REQUEST_COMMENTED,
        "New comment",
        f"New comment on {request.title}.",
        "maintenance_request",
        request.id,
    )


def notify_work_order_assigned(
    context: OrgContext, order: WorkOrder, request: MaintenanceRequest
) -> None:
    _add(
        context,
        _contractor_login(context.organization_id, order.contractor_id),
        NotificationKind.WORK_ORDER_ASSIGNED,
        "New work order",
        request.title,
        "work_order",
        order.id,
    )


def notify_work_order_status(
    context: OrgContext, order: WorkOrder, request: MaintenanceRequest
) -> None:
    if context.role == MembershipRole.CONTRACTOR:
        recipients = _responsible_staff(context.organization_id, request.property_id)
    else:
        recipients = _contractor_login(context.organization_id, order.contractor_id)
    _add(
        context,
        recipients,
        NotificationKind.WORK_ORDER_STATUS_CHANGED,
        "Work order updated",
        f"{request.title}: {_label(order.status)}.",
        "work_order",
        order.id,
    )


# --- Reading --------------------------------------------------------------------------------


def notification_view(notification: Notification) -> dict[str, Any]:
    return {
        "id": notification.id,
        "kind": notification.kind,
        "title": notification.title,
        "body": notification.body,
        "resource_type": notification.resource_type,
        "resource_id": notification.resource_id,
        "read": notification.read_at is not None,
        "created_at": notification.created_at,
    }


def _own(context: OrgContext) -> Any:
    return select(Notification).where(
        Notification.organization_id == context.organization_id,
        Notification.recipient_membership_id == context.membership_id,
    )


def list_notifications(
    context: OrgContext, *, unread_only: bool, limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    stmt = _own(context)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    items, next_cursor = paginate(
        stmt,
        created_column=Notification.created_at,
        id_column=Notification.id,
        limit=limit,
        cursor=cursor,
    )
    return [notification_view(item) for item in items], next_cursor


def unread_count(context: OrgContext) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.organization_id == context.organization_id,
            Notification.recipient_membership_id == context.membership_id,
            Notification.read_at.is_(None),
        )
    )
    return int(db.session.execute(stmt).scalar_one())


def mark_read(context: OrgContext, notification_id: uuid.UUID) -> dict[str, Any]:
    notification = db.session.execute(
        _own(context).where(Notification.id == notification_id)
    ).scalar_one_or_none()
    if notification is None:  # someone else's notification looks exactly like a missing one
        raise NotFoundError()
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.session.commit()
    return notification_view(notification)


def mark_all_read(context: OrgContext) -> int:
    marked = db.session.execute(
        update(Notification)
        .where(
            Notification.organization_id == context.organization_id,
            Notification.recipient_membership_id == context.membership_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
        .returning(Notification.id)
    ).scalars()
    count = len(list(marked))
    db.session.commit()
    return count
