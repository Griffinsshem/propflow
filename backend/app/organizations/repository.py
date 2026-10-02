"""Data access for organizations, memberships and invitations.

Every query is organization-scoped, except lookups by a secret invitation token.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select, update

from app.auth.models import User
from app.extensions import db
from app.organizations.models import (
    Invitation,
    MembershipRole,
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)


def get_organization(organization_id: uuid.UUID) -> Organization | None:
    return db.session.get(Organization, organization_id)


def lock_organization(organization_id: uuid.UUID) -> Organization | None:
    """Row lock that serializes membership changes per organization (last-owner protection)."""
    return db.session.get(Organization, organization_id, with_for_update=True)


def get_active_membership(
    user_id: uuid.UUID, organization_id: uuid.UUID
) -> OrganizationMembership | None:
    """Active membership in an active organization (served by the unique (org, user) index)."""
    stmt = (
        select(OrganizationMembership)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
            Organization.status == OrganizationStatus.ACTIVE,
        )
    )
    return db.session.execute(stmt).scalar_one_or_none()


def get_membership(user_id: uuid.UUID, organization_id: uuid.UUID) -> OrganizationMembership | None:
    """Any status: used to reactivate a former member who accepts a new invitation."""
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.organization_id == organization_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def members_query(organization_id: uuid.UUID) -> Select[OrganizationMembership, User]:
    return (
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(OrganizationMembership.organization_id == organization_id)
    )


def get_member(
    organization_id: uuid.UUID, membership_id: uuid.UUID
) -> tuple[OrganizationMembership, User] | None:
    stmt = members_query(organization_id).where(OrganizationMembership.id == membership_id)
    row = db.session.execute(stmt).first()
    return (row[0], row[1]) if row is not None else None


def count_active_owners(organization_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == MembershipRole.OWNER,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
        )
    )
    return int(db.session.execute(stmt).scalar_one())


def revoke_pending_invitations(
    organization_id: uuid.UUID, email: str, revoked_at: datetime
) -> None:
    db.session.execute(
        update(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
    )


def get_invitation(organization_id: uuid.UUID, invitation_id: uuid.UUID) -> Invitation | None:
    stmt = select(Invitation).where(
        Invitation.id == invitation_id, Invitation.organization_id == organization_id
    )
    return db.session.execute(stmt).scalar_one_or_none()


def get_invitation_by_token_hash(token_hash: str, *, lock: bool = False) -> Invitation | None:
    stmt = select(Invitation).where(Invitation.token_hash == token_hash)
    if lock:
        stmt = stmt.with_for_update()
    return db.session.execute(stmt).scalar_one_or_none()


def pending_invitations_query(organization_id: uuid.UUID, now: datetime) -> Select[Any]:
    return select(Invitation).where(
        Invitation.organization_id == organization_id,
        Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None),
        Invitation.expires_at > now,
    )
