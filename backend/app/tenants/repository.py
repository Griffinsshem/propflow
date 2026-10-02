"""Data access for tenant profiles.

Visibility: owner sees every tenant; a manager only tenants placed in units of their
assigned properties; tenants see only themselves (via /tenants/me); contractors none.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, false, func, select

from app.auth.models import User
from app.authz.context import OrgContext
from app.extensions import db
from app.organizations.models import MembershipRole, MembershipStatus, OrganizationMembership
from app.properties.models import Property, Unit
from app.properties.repository import assigned_property_ids
from app.tenants.models import TenantProfile

TenantRow = tuple[TenantProfile, OrganizationMembership, User, Unit | None, Property | None]
TenantSelect = Select[TenantProfile, OrganizationMembership, User, Unit, Property]


def _tenant_rows(organization_id: uuid.UUID) -> TenantSelect:
    return (
        select(TenantProfile, OrganizationMembership, User, Unit, Property)
        .join(OrganizationMembership, OrganizationMembership.id == TenantProfile.membership_id)
        .join(User, User.id == OrganizationMembership.user_id)
        .outerjoin(Unit, Unit.id == TenantProfile.unit_id)
        .outerjoin(Property, Property.id == Unit.property_id)
        .where(
            TenantProfile.organization_id == organization_id,
            OrganizationMembership.role == MembershipRole.TENANT,
        )
    )


def visible_tenants(context: OrgContext) -> TenantSelect:
    stmt = _tenant_rows(context.organization_id)
    if context.role == MembershipRole.OWNER:
        return stmt
    if context.role == MembershipRole.MANAGER:
        return stmt.where(Unit.property_id.in_(assigned_property_ids(context)))
    return stmt.where(false())


def _first(stmt: TenantSelect) -> TenantRow | None:
    row = db.session.execute(stmt).first()
    return (row[0], row[1], row[2], row[3], row[4]) if row is not None else None


def get_visible_tenant(context: OrgContext, tenant_id: uuid.UUID) -> TenantRow | None:
    return _first(visible_tenants(context).where(TenantProfile.id == tenant_id))


def get_tenant_row(organization_id: uuid.UUID, tenant_id: uuid.UUID) -> TenantRow | None:
    """Unscoped within the org: only for re-reading a row the caller was just allowed to change."""
    return _first(_tenant_rows(organization_id).where(TenantProfile.id == tenant_id))


def get_own_tenant(context: OrgContext) -> TenantRow | None:
    stmt = _tenant_rows(context.organization_id).where(
        TenantProfile.membership_id == context.membership_id
    )
    return _first(stmt)


def get_profile_by_membership(
    organization_id: uuid.UUID, membership_id: uuid.UUID
) -> TenantProfile | None:
    stmt = select(TenantProfile).where(
        TenantProfile.organization_id == organization_id,
        TenantProfile.membership_id == membership_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def count_active_tenants_in_unit(organization_id: uuid.UUID, unit_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(TenantProfile)
        .join(OrganizationMembership, OrganizationMembership.id == TenantProfile.membership_id)
        .where(
            TenantProfile.organization_id == organization_id,
            TenantProfile.unit_id == unit_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
            OrganizationMembership.role == MembershipRole.TENANT,
        )
    )
    return int(db.session.execute(stmt).scalar_one())
