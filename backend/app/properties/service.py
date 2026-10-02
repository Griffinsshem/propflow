"""Property, building, unit and manager-assignment use cases. One transaction each."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.audit import service as audit
from app.authz.context import OrgContext
from app.common.errors import ConflictError, NotFoundError, RequestValidationError
from app.common.pagination import paginate
from app.extensions import db
from app.organizations import repository as org_repository
from app.organizations.models import MembershipRole, MembershipStatus
from app.properties import repository
from app.properties.models import Building, Property, PropertyAssignment, Unit

STALE = "This record was changed by someone else. Reload it and try again."
DUPLICATE_UNIT = "A unit with this label already exists in this property."
DUPLICATE_BUILDING = "A building with this name already exists in this property."
PROPERTY_IN_USE = "Properties with buildings or units cannot be deleted. Archive it instead."


def _jsonable(value: Any) -> Any:
    return str(value) if isinstance(value, uuid.UUID) else value


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    """Trim strings; blank optional strings become NULL."""
    return {
        key: (value.strip() or None) if isinstance(value, str) else value
        for key, value in data.items()
    }


def _apply(
    entity: Property | Unit, changes: dict[str, Any], expected_version: int
) -> dict[str, Any]:
    """Applies changes if the client saw the current version; returns an audit-ready diff."""
    if entity.version != expected_version:
        raise ConflictError(STALE)
    diff: dict[str, Any] = {}
    for field, value in changes.items():
        current = getattr(entity, field)
        if current != value:
            diff[field] = {"from": _jsonable(current), "to": _jsonable(value)}
            setattr(entity, field, value)
    return diff


def _flush(conflict_message: str) -> None:
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError(conflict_message) from exc


def _commit(conflict_message: str) -> None:
    try:
        db.session.commit()
    except StaleDataError as exc:  # concurrent update between our read and write
        db.session.rollback()
        raise ConflictError(STALE) from exc
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError(conflict_message) from exc


# --- Properties ---------------------------------------------------------------------------


def list_properties(
    context: OrgContext, *, status: str, limit: int, cursor: str | None
) -> tuple[list[Property], str | None]:
    stmt = repository.visible_properties(context).where(Property.status == status)
    return paginate(
        stmt, created_column=Property.created_at, id_column=Property.id, limit=limit, cursor=cursor
    )


def get_property(context: OrgContext, property_id: uuid.UUID) -> Property:
    prop = repository.get_visible_property(context, property_id)
    if prop is None:
        raise NotFoundError()
    return prop


def create_property(context: OrgContext, data: dict[str, Any]) -> Property:
    data = _clean(data)
    prop = Property(
        organization_id=context.organization_id,
        name=data["name"],
        property_type=data["property_type"],
        address_line=data["address_line"],
        city=data["city"],
        region=data.get("region"),
        country_code=data["country_code"],
        description=data.get("description"),
    )
    db.session.add(prop)
    db.session.flush()
    audit.record(
        "property.created",
        "property",
        prop.id,
        organization_id=context.organization_id,
        details={"name": prop.name},
    )
    _commit("This property could not be created.")
    return prop


def update_property(context: OrgContext, property_id: uuid.UUID, data: dict[str, Any]) -> Property:
    prop = get_property(context, property_id)
    expected_version = data.pop("version")
    diff = _apply(prop, _clean(data), expected_version)
    if diff:
        audit.record(
            "property.updated",
            "property",
            prop.id,
            organization_id=context.organization_id,
            details=diff,
        )
    _commit("This property could not be updated.")
    return prop


def delete_property(context: OrgContext, property_id: uuid.UUID) -> None:
    prop = get_property(context, property_id)
    audit.record(
        "property.deleted",
        "property",
        prop.id,
        organization_id=context.organization_id,
        details={"name": prop.name},
    )
    db.session.delete(prop)
    _commit(PROPERTY_IN_USE)  # RESTRICT foreign keys refuse if buildings/units exist


# --- Buildings ----------------------------------------------------------------------------


def list_buildings(context: OrgContext, property_id: uuid.UUID) -> list[Building]:
    get_property(context, property_id)
    return repository.list_buildings(context.organization_id, property_id)


def create_building(context: OrgContext, property_id: uuid.UUID, name: str) -> Building:
    prop = get_property(context, property_id)
    building = Building(
        organization_id=context.organization_id, property_id=prop.id, name=name.strip()
    )
    db.session.add(building)
    _flush(DUPLICATE_BUILDING)
    audit.record(
        "building.created",
        "building",
        building.id,
        organization_id=context.organization_id,
        details={"property_id": str(prop.id), "name": building.name},
    )
    _commit(DUPLICATE_BUILDING)
    return building


def rename_building(
    context: OrgContext, property_id: uuid.UUID, building_id: uuid.UUID, name: str
) -> Building:
    get_property(context, property_id)
    building = repository.get_building(context.organization_id, property_id, building_id)
    if building is None:
        raise NotFoundError()
    previous = building.name
    building.name = name.strip()
    if building.name != previous:
        audit.record(
            "building.updated",
            "building",
            building.id,
            organization_id=context.organization_id,
            details={"name": {"from": previous, "to": building.name}},
        )
    _commit(DUPLICATE_BUILDING)
    return building


# --- Units --------------------------------------------------------------------------------


def _require_building_in_property(
    context: OrgContext, property_id: uuid.UUID, building_id: uuid.UUID | None
) -> None:
    if building_id is None:
        return
    if repository.get_building(context.organization_id, property_id, building_id) is None:
        raise RequestValidationError(
            "The building does not belong to this property.",
            details={"json": {"building_id": ["Not a building of this property."]}},
        )


def list_units(
    context: OrgContext,
    *,
    property_id: uuid.UUID | None,
    building_id: uuid.UUID | None,
    status: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[Unit], str | None]:
    stmt = repository.visible_units(context)
    if property_id is not None:
        stmt = stmt.where(Unit.property_id == property_id)
    if building_id is not None:
        stmt = stmt.where(Unit.building_id == building_id)
    if status is not None:
        stmt = stmt.where(Unit.status == status)
    return paginate(
        stmt, created_column=Unit.created_at, id_column=Unit.id, limit=limit, cursor=cursor
    )


def get_unit(context: OrgContext, unit_id: uuid.UUID) -> Unit:
    unit = repository.get_visible_unit(context, unit_id)
    if unit is None:
        raise NotFoundError()
    return unit


def create_unit(context: OrgContext, data: dict[str, Any]) -> Unit:
    prop = get_property(context, data["property_id"])  # 404 unless visible to the caller
    _require_building_in_property(context, prop.id, data.get("building_id"))
    unit = Unit(
        organization_id=context.organization_id,
        property_id=prop.id,
        building_id=data.get("building_id"),
        label=data["label"].strip(),
        floor=data.get("floor"),
        bedrooms=data.get("bedrooms"),
        status=data["status"],
    )
    db.session.add(unit)
    _flush(DUPLICATE_UNIT)
    audit.record(
        "unit.created",
        "unit",
        unit.id,
        organization_id=context.organization_id,
        details={"property_id": str(prop.id), "label": unit.label},
    )
    _commit(DUPLICATE_UNIT)
    return unit


def update_unit(context: OrgContext, unit_id: uuid.UUID, data: dict[str, Any]) -> Unit:
    unit = get_unit(context, unit_id)
    expected_version = data.pop("version")
    if "building_id" in data:
        _require_building_in_property(context, unit.property_id, data["building_id"])
    diff = _apply(unit, _clean(data), expected_version)
    if diff:
        audit.record(
            "unit.updated", "unit", unit.id, organization_id=context.organization_id, details=diff
        )
    _commit(DUPLICATE_UNIT)
    return unit


# --- Manager assignments ------------------------------------------------------------------


def _manager_view(assignment: PropertyAssignment, membership: Any, user: Any) -> dict[str, Any]:
    return {
        "membership_id": membership.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "assigned_at": assignment.created_at,
    }


def list_property_managers(context: OrgContext, property_id: uuid.UUID) -> list[dict[str, Any]]:
    get_property(context, property_id)
    return [
        _manager_view(assignment, membership, user)
        for assignment, membership, user in repository.list_assignments(
            context.organization_id, property_id
        )
    ]


def assign_manager(
    context: OrgContext, property_id: uuid.UUID, membership_id: uuid.UUID
) -> dict[str, Any]:
    prop = get_property(context, property_id)
    found = org_repository.get_member(context.organization_id, membership_id)
    if found is None:
        raise NotFoundError()
    membership, user = found
    if membership.role != MembershipRole.MANAGER or membership.status != MembershipStatus.ACTIVE:
        raise RequestValidationError(
            "Only active managers can be assigned to a property.",
            details={"json": {"membership_id": ["Not an active manager."]}},
        )
    assignment = repository.get_assignment(context.organization_id, prop.id, membership.id)
    if assignment is None:  # idempotent: assigning twice is not an error
        assignment = PropertyAssignment(
            organization_id=context.organization_id,
            property_id=prop.id,
            membership_id=membership.id,
        )
        db.session.add(assignment)
        _flush("This manager is already assigned to the property.")
        audit.record(
            "property.manager_assigned",
            "property",
            prop.id,
            organization_id=context.organization_id,
            details={"membership_id": str(membership.id), "user_id": str(user.id)},
        )
        _commit("This manager is already assigned to the property.")
    return _manager_view(assignment, membership, user)


def unassign_manager(context: OrgContext, property_id: uuid.UUID, membership_id: uuid.UUID) -> None:
    prop = get_property(context, property_id)
    assignment = repository.get_assignment(context.organization_id, prop.id, membership_id)
    if assignment is None:
        raise NotFoundError()
    db.session.delete(assignment)
    audit.record(
        "property.manager_unassigned",
        "property",
        prop.id,
        organization_id=context.organization_id,
        details={"membership_id": str(membership_id)},
    )
    _commit("The manager could not be unassigned.")
