"""Data access for the property hierarchy. Every query is organization-scoped.

Visibility rules (object-level authorization) live here, in one place:
- owner:   every property and unit in the organization
- manager: only properties assigned to their membership, and the units inside them
- tenant:  their own unit once tenancies exist (Phase 6); no property listing
- contractor: none
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, false, select

from app.auth.models import User
from app.authz.context import OrgContext
from app.extensions import db
from app.organizations.models import MembershipRole, OrganizationMembership
from app.properties.models import Building, Property, PropertyAssignment, Unit

MAX_BUILDINGS_PER_PROPERTY_LIST = 200


def _assigned_property_ids(context: OrgContext) -> Select[uuid.UUID]:
    return select(PropertyAssignment.property_id).where(
        PropertyAssignment.organization_id == context.organization_id,
        PropertyAssignment.membership_id == context.membership_id,
    )


def visible_properties(context: OrgContext) -> Select[Property]:
    stmt = select(Property).where(Property.organization_id == context.organization_id)
    if context.role == MembershipRole.OWNER:
        return stmt
    if context.role == MembershipRole.MANAGER:
        return stmt.where(Property.id.in_(_assigned_property_ids(context)))
    return stmt.where(false())


def get_visible_property(context: OrgContext, property_id: uuid.UUID) -> Property | None:
    stmt = visible_properties(context).where(Property.id == property_id)
    return db.session.execute(stmt).scalar_one_or_none()


def visible_units(context: OrgContext) -> Select[Unit]:
    stmt = select(Unit).where(Unit.organization_id == context.organization_id)
    if context.role == MembershipRole.OWNER:
        return stmt
    if context.role == MembershipRole.MANAGER:
        return stmt.where(Unit.property_id.in_(_assigned_property_ids(context)))
    return stmt.where(false())  # tenants gain their own unit in Phase 6


def get_visible_unit(context: OrgContext, unit_id: uuid.UUID) -> Unit | None:
    stmt = visible_units(context).where(Unit.id == unit_id)
    return db.session.execute(stmt).scalar_one_or_none()


def get_building(
    organization_id: uuid.UUID, property_id: uuid.UUID, building_id: uuid.UUID
) -> Building | None:
    stmt = select(Building).where(
        Building.id == building_id,
        Building.property_id == property_id,
        Building.organization_id == organization_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def list_buildings(organization_id: uuid.UUID, property_id: uuid.UUID) -> list[Building]:
    stmt = (
        select(Building)
        .where(Building.organization_id == organization_id, Building.property_id == property_id)
        .order_by(Building.name)
        .limit(MAX_BUILDINGS_PER_PROPERTY_LIST)
    )
    return list(db.session.execute(stmt).scalars())


def get_assignment(
    organization_id: uuid.UUID, property_id: uuid.UUID, membership_id: uuid.UUID
) -> PropertyAssignment | None:
    stmt = select(PropertyAssignment).where(
        PropertyAssignment.organization_id == organization_id,
        PropertyAssignment.property_id == property_id,
        PropertyAssignment.membership_id == membership_id,
    )
    return db.session.execute(stmt).scalar_one_or_none()


def list_assignments(
    organization_id: uuid.UUID, property_id: uuid.UUID
) -> list[tuple[PropertyAssignment, OrganizationMembership, User]]:
    stmt = (
        select(PropertyAssignment, OrganizationMembership, User)
        .join(OrganizationMembership, OrganizationMembership.id == PropertyAssignment.membership_id)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(
            PropertyAssignment.organization_id == organization_id,
            PropertyAssignment.property_id == property_id,
        )
        .order_by(PropertyAssignment.created_at)
    )
    return [(a, m, u) for a, m, u in db.session.execute(stmt)]
