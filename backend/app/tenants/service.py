"""Tenant profiles and unit placement (spec 3.3).

Unit occupancy follows placements: `occupied` while any active tenant is placed, `vacant`
when the last one leaves. Units a manager marked `unavailable` are left alone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm.exc import StaleDataError

from app.audit import service as audit
from app.authz.context import OrgContext
from app.common.errors import ConflictError, NotFoundError
from app.common.pagination import paginate
from app.extensions import db
from app.organizations.models import MembershipStatus, OrganizationMembership
from app.properties import repository as properties_repository
from app.properties.models import Unit, UnitStatus
from app.tenants import repository
from app.tenants.models import TenantProfile
from app.tenants.repository import TenantRow

STALE = "This record was changed by someone else. Reload it and try again."


def _today() -> date:
    return datetime.now(UTC).date()


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def tenant_view(row: TenantRow) -> dict[str, Any]:
    profile, membership, user, unit, prop = row
    return {
        "id": profile.id,
        "membership_id": membership.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": profile.phone,
        "status": membership.status,
        "move_in_date": profile.move_in_date,
        "version": profile.version,
        "unit": None
        if unit is None
        else {
            "id": unit.id,
            "label": unit.label,
            "building_id": unit.building_id,
            "property_id": unit.property_id,
            "property_name": prop.name if prop is not None else None,
        },
    }


# --- Hooks used by invitation acceptance and membership changes ---------------------------


def _sync_unit_status(unit_id: uuid.UUID) -> None:
    unit = db.session.get(Unit, unit_id)
    if unit is None or unit.status == UnitStatus.UNAVAILABLE:
        return
    occupied = repository.count_active_tenants_in_unit(unit.organization_id, unit.id) > 0
    target = UnitStatus.OCCUPIED if occupied else UnitStatus.VACANT
    if unit.status != target:
        unit.status = target


def _move(profile: TenantProfile, unit_id: uuid.UUID | None) -> None:
    previous = profile.unit_id
    if previous == unit_id:
        return
    profile.unit_id = unit_id
    profile.move_in_date = _today() if unit_id is not None else None
    db.session.flush()
    for affected in (previous, unit_id):
        if affected is not None:
            _sync_unit_status(affected)


def place_tenant(
    organization_id: uuid.UUID, membership_id: uuid.UUID, unit_id: uuid.UUID | None
) -> TenantProfile:
    """Creates the profile if needed and places the tenant in `unit_id` (if given)."""
    profile = repository.get_profile_by_membership(organization_id, membership_id)
    if profile is None:
        profile = TenantProfile(
            organization_id=organization_id,
            membership_id=membership_id,
            unit_id=unit_id,
            move_in_date=_today() if unit_id is not None else None,
        )
        db.session.add(profile)
        db.session.flush()
        if unit_id is not None:
            _sync_unit_status(unit_id)
        return profile
    if unit_id is not None:
        _move(profile, unit_id)
    return profile


def ensure_profile(organization_id: uuid.UUID, membership_id: uuid.UUID) -> TenantProfile:
    return place_tenant(organization_id, membership_id, None)


def release_membership(organization_id: uuid.UUID, membership_id: uuid.UUID) -> None:
    """Frees the unit when a tenant is deactivated or leaves the tenant role."""
    profile = repository.get_profile_by_membership(organization_id, membership_id)
    if profile is not None:
        _move(profile, None)


# --- Use cases ------------------------------------------------------------------------------


def list_tenants(
    context: OrgContext,
    *,
    status: str,
    unit_id: uuid.UUID | None,
    property_id: uuid.UUID | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    stmt = repository.visible_tenants(context).where(OrganizationMembership.status == status)
    if unit_id is not None:
        stmt = stmt.where(TenantProfile.unit_id == unit_id)
    if property_id is not None:
        stmt = stmt.where(Unit.property_id == property_id)
    rows, next_cursor = paginate(
        stmt,
        created_column=TenantProfile.created_at,
        id_column=TenantProfile.id,
        limit=limit,
        cursor=cursor,
        scalars=False,
    )
    return [tenant_view(tuple(row)) for row in rows], next_cursor


def _visible_row(context: OrgContext, tenant_id: uuid.UUID) -> TenantRow:
    row = repository.get_visible_tenant(context, tenant_id)
    if row is None:
        raise NotFoundError()
    return row


def get_tenant(context: OrgContext, tenant_id: uuid.UUID) -> dict[str, Any]:
    return tenant_view(_visible_row(context, tenant_id))


def membership_id_of(context: OrgContext, tenant_id: uuid.UUID) -> uuid.UUID:
    return _visible_row(context, tenant_id)[1].id


def my_tenancy(context: OrgContext) -> dict[str, Any]:
    row = repository.get_own_tenant(context)
    if row is None:
        raise NotFoundError("You do not have a tenant profile in this organization.")
    return tenant_view(row)


def update_tenant(
    context: OrgContext, tenant_id: uuid.UUID, data: dict[str, Any]
) -> dict[str, Any]:
    profile, membership, *_ = _visible_row(context, tenant_id)
    if membership.status != MembershipStatus.ACTIVE:
        raise ConflictError("This tenant is deactivated.")
    if profile.version != data.pop("version"):
        raise ConflictError(STALE)

    diff: dict[str, Any] = {}
    if "unit_id" in data and data["unit_id"] != profile.unit_id:
        new_unit_id = data["unit_id"]
        # The destination must be visible too: a manager can't move tenants out of scope.
        if (
            new_unit_id is not None
            and properties_repository.get_visible_unit(context, new_unit_id) is None
        ):
            raise NotFoundError()
        diff["unit_id"] = {"from": _jsonable(profile.unit_id), "to": _jsonable(new_unit_id)}
        _move(profile, new_unit_id)
    if "phone" in data and data["phone"] != profile.phone:
        profile.phone = data["phone"]
        diff["phone"] = "changed"  # the number itself stays out of the audit trail
    if "move_in_date" in data and data["move_in_date"] != profile.move_in_date:
        diff["move_in_date"] = {
            "from": _jsonable(profile.move_in_date),
            "to": _jsonable(data["move_in_date"]),
        }
        profile.move_in_date = data["move_in_date"]

    if diff:
        audit.record(
            "tenant.updated",
            "tenant",
            profile.id,
            organization_id=context.organization_id,
            details=diff,
        )
    try:
        db.session.commit()
    except StaleDataError as exc:
        db.session.rollback()
        raise ConflictError(STALE) from exc
    row = repository.get_tenant_row(context.organization_id, tenant_id)
    if row is None:
        raise NotFoundError()
    return tenant_view(row)
