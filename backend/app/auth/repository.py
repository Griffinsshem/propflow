"""Data access for authentication. Queries only; business rules live in the service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update

from app.auth.models import User, UserSession
from app.extensions import db
from app.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)


def get_user(user_id: uuid.UUID) -> User | None:
    return db.session.get(User, user_id)


def get_user_by_email(email: str) -> User | None:
    return db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_session_by_token_hash(token_hash: str) -> UserSession | None:
    stmt = select(UserSession).where(UserSession.token_hash == token_hash)
    return db.session.execute(stmt).scalar_one_or_none()


def list_active_memberships(
    user_id: uuid.UUID,
) -> list[tuple[OrganizationMembership, Organization]]:
    """One query (no N+1): the user's active memberships in active organizations."""
    stmt = (
        select(OrganizationMembership, Organization)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
            Organization.status == OrganizationStatus.ACTIVE,
        )
        .order_by(Organization.name)
    )
    return [(membership, org) for membership, org in db.session.execute(stmt)]


def revoke_all_sessions(user_id: uuid.UUID, revoked_at: datetime) -> None:
    """Single UPDATE, no per-row round trips."""
    db.session.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
