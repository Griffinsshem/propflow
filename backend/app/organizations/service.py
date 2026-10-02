"""Organization use cases. Authorization uses the caller's membership in the target org."""

from __future__ import annotations

import uuid
from typing import Any

from app.audit import service as audit
from app.auth import repository as auth_repository
from app.auth.models import User, UserSession
from app.authz.permissions import Permission, has_permission
from app.common.errors import NotFoundError, PermissionDeniedError
from app.extensions import db
from app.organizations import repository
from app.organizations.models import MembershipRole, Organization, OrganizationMembership


def organization_view(org: Organization, role: str) -> dict[str, Any]:
    return {
        "id": org.id,
        "name": org.name,
        "status": org.status,
        "role": role,
        "created_at": org.created_at,
    }


def _membership_or_404(user_id: uuid.UUID, organization_id: uuid.UUID) -> OrganizationMembership:
    membership = repository.get_active_membership(user_id, organization_id)
    if membership is None:
        # Identical whether the org doesn't exist or belongs to someone else (no enumeration).
        raise NotFoundError()
    return membership


def _organization(organization_id: uuid.UUID) -> Organization:
    org = repository.get_organization(organization_id)
    if org is None:
        raise NotFoundError()
    return org


def list_for_user(user_id: uuid.UUID) -> list[dict[str, Any]]:
    return [
        organization_view(org, membership.role)
        for membership, org in auth_repository.list_active_memberships(user_id)
    ]


def create(user: User, session: UserSession | None, name: str) -> dict[str, Any]:
    """Org + owner membership + session switch + audit entry: one transaction."""
    org = Organization(name=name.strip())
    db.session.add(org)
    db.session.flush()
    db.session.add(
        OrganizationMembership(organization_id=org.id, user_id=user.id, role=MembershipRole.OWNER)
    )
    if session is not None:
        session.active_organization_id = org.id
    audit.record(
        "organization.created",
        "organization",
        org.id,
        organization_id=org.id,
        details={"name": org.name},
    )
    db.session.commit()
    return organization_view(org, MembershipRole.OWNER)


def get_for_member(user_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, Any]:
    membership = _membership_or_404(user_id, organization_id)
    return organization_view(_organization(organization_id), membership.role)


def rename(user_id: uuid.UUID, organization_id: uuid.UUID, name: str) -> dict[str, Any]:
    membership = _membership_or_404(user_id, organization_id)
    if not has_permission(membership.role, Permission.ORGANIZATION_UPDATE):
        raise PermissionDeniedError()
    org = _organization(organization_id)
    previous = org.name
    org.name = name.strip()
    audit.record(
        "organization.updated",
        "organization",
        org.id,
        organization_id=org.id,
        details={"name": {"from": previous, "to": org.name}},
    )
    db.session.commit()
    return organization_view(org, membership.role)


def activate(
    user_id: uuid.UUID, session: UserSession, organization_id: uuid.UUID
) -> dict[str, Any]:
    membership = _membership_or_404(user_id, organization_id)
    session.active_organization_id = organization_id
    db.session.commit()
    return organization_view(_organization(organization_id), membership.role)
