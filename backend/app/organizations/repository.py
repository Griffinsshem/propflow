"""Data access for organizations and memberships."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.extensions import db
from app.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)


def get_organization(organization_id: uuid.UUID) -> Organization | None:
    return db.session.get(Organization, organization_id)


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
