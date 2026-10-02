"""Member management. Changes lock the organization row first, so concurrent requests are
serialized and can never leave an organization without an active owner."""

from __future__ import annotations

import uuid
from typing import Any

from app.audit import service as audit
from app.auth.models import User
from app.authz.context import OrgContext
from app.authz.policies import can_deactivate
from app.common.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.common.pagination import paginate
from app.extensions import db
from app.organizations import repository
from app.organizations.models import MembershipRole, MembershipStatus, OrganizationMembership

LAST_OWNER = "An organization must keep at least one active owner."


def member_view(membership: OrganizationMembership, user: User) -> dict[str, Any]:
    return {
        "id": membership.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": membership.role,
        "status": membership.status,
        "joined_at": membership.created_at,
    }


def list_members(
    context: OrgContext, *, limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    rows, next_cursor = paginate(
        repository.members_query(context.organization_id),
        created_column=OrganizationMembership.created_at,
        id_column=OrganizationMembership.id,
        limit=limit,
        cursor=cursor,
        scalars=False,
    )
    return [member_view(membership, user) for membership, user in rows], next_cursor


def _locked_member(
    context: OrgContext, membership_id: uuid.UUID
) -> tuple[OrganizationMembership, User]:
    repository.lock_organization(context.organization_id)
    found = repository.get_member(context.organization_id, membership_id)
    if found is None:
        raise NotFoundError()
    return found


def _is_last_active_owner(organization_id: uuid.UUID, membership: OrganizationMembership) -> bool:
    return (
        membership.role == MembershipRole.OWNER
        and membership.status == MembershipStatus.ACTIVE
        and repository.count_active_owners(organization_id) <= 1
    )


def change_role(context: OrgContext, membership_id: uuid.UUID, role: str) -> dict[str, Any]:
    membership, user = _locked_member(context, membership_id)
    new_role = MembershipRole(role)
    if membership.role != new_role:
        if _is_last_active_owner(context.organization_id, membership):
            raise ConflictError(LAST_OWNER)
        previous = membership.role
        membership.role = new_role
        audit.record(
            "membership.role_changed",
            "membership",
            membership.id,
            organization_id=context.organization_id,
            details={"user_id": str(user.id), "from": previous, "to": new_role.value},
        )
    db.session.commit()  # also releases the organization lock on the no-op path
    return member_view(membership, user)


def deactivate(context: OrgContext, membership_id: uuid.UUID) -> dict[str, Any]:
    membership, user = _locked_member(context, membership_id)
    if not can_deactivate(context.role, membership.role):
        raise PermissionDeniedError()
    if membership.status == MembershipStatus.ACTIVE:
        if _is_last_active_owner(context.organization_id, membership):
            raise ConflictError(LAST_OWNER)
        membership.status = MembershipStatus.DEACTIVATED
        audit.record(
            "membership.deactivated",
            "membership",
            membership.id,
            organization_id=context.organization_id,
            details={"user_id": str(user.id), "role": membership.role},
        )
    db.session.commit()
    return member_view(membership, user)
