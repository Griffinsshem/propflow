"""Property hierarchy endpoints: a thin HTTP layer over app.properties.service."""

from __future__ import annotations

import uuid
from typing import Any

from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.properties import service
from app.properties.models import Building, Property, Unit
from app.properties.schemas import (
    BuildingSchema,
    BuildingWriteSchema,
    ManagerAssignSchema,
    PropertyCreateSchema,
    PropertyListQuerySchema,
    PropertyManagerSchema,
    PropertyPageSchema,
    PropertySchema,
    PropertyUpdateSchema,
    UnitCreateSchema,
    UnitListQuerySchema,
    UnitPageSchema,
    UnitSchema,
    UnitUpdateSchema,
)

properties_blp = Blueprint(
    "properties",
    __name__,
    url_prefix="/api/v1/properties",
    description="Properties, buildings and manager assignments.",
)
units_blp = Blueprint("units", __name__, url_prefix="/api/v1/units", description="Units.")


@properties_blp.get("")
@properties_blp.arguments(PropertyListQuerySchema, location="query")
@properties_blp.response(200, PropertyPageSchema)
@require_permission(Permission.PROPERTY_READ)
def list_properties(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = service.list_properties(
        current_org_context(), status=query["status"], limit=query["limit"], cursor=query["cursor"]
    )
    return {"items": items, "next_cursor": next_cursor}


@properties_blp.post("")
@properties_blp.arguments(PropertyCreateSchema)
@properties_blp.response(201, PropertySchema)
@require_permission(Permission.PROPERTY_CREATE)
def create_property(payload: dict[str, Any]) -> Property:
    return service.create_property(current_org_context(), payload)


@properties_blp.get("/<uuid:property_id>")
@properties_blp.response(200, PropertySchema)
@require_permission(Permission.PROPERTY_READ)
def get_property(property_id: uuid.UUID) -> Property:
    return service.get_property(current_org_context(), property_id)


@properties_blp.patch("/<uuid:property_id>")
@properties_blp.arguments(PropertyUpdateSchema)
@properties_blp.response(200, PropertySchema)
@require_permission(Permission.PROPERTY_UPDATE)
def update_property(payload: dict[str, Any], property_id: uuid.UUID) -> Property:
    return service.update_property(current_org_context(), property_id, payload)


@properties_blp.delete("/<uuid:property_id>")
@properties_blp.response(204)
@require_permission(Permission.PROPERTY_DELETE)
def delete_property(property_id: uuid.UUID) -> None:
    service.delete_property(current_org_context(), property_id)


@properties_blp.get("/<uuid:property_id>/buildings")
@properties_blp.response(200, BuildingSchema(many=True))
@require_permission(Permission.PROPERTY_READ)
def list_buildings(property_id: uuid.UUID) -> list[Building]:
    return service.list_buildings(current_org_context(), property_id)


@properties_blp.post("/<uuid:property_id>/buildings")
@properties_blp.arguments(BuildingWriteSchema)
@properties_blp.response(201, BuildingSchema)
@require_permission(Permission.PROPERTY_UPDATE)
def create_building(payload: dict[str, Any], property_id: uuid.UUID) -> Building:
    return service.create_building(current_org_context(), property_id, payload["name"])


@properties_blp.patch("/<uuid:property_id>/buildings/<uuid:building_id>")
@properties_blp.arguments(BuildingWriteSchema)
@properties_blp.response(200, BuildingSchema)
@require_permission(Permission.PROPERTY_UPDATE)
def rename_building(
    payload: dict[str, Any], property_id: uuid.UUID, building_id: uuid.UUID
) -> Building:
    return service.rename_building(current_org_context(), property_id, building_id, payload["name"])


@properties_blp.get("/<uuid:property_id>/managers")
@properties_blp.response(200, PropertyManagerSchema(many=True))
@require_permission(Permission.PROPERTY_UPDATE)
def list_property_managers(property_id: uuid.UUID) -> list[dict[str, Any]]:
    return service.list_property_managers(current_org_context(), property_id)


@properties_blp.post("/<uuid:property_id>/managers")
@properties_blp.arguments(ManagerAssignSchema)
@properties_blp.response(200, PropertyManagerSchema)
@require_permission(Permission.PROPERTY_UPDATE)
def assign_manager(payload: dict[str, Any], property_id: uuid.UUID) -> dict[str, Any]:
    return service.assign_manager(current_org_context(), property_id, payload["membership_id"])


@properties_blp.delete("/<uuid:property_id>/managers/<uuid:membership_id>")
@properties_blp.response(204)
@require_permission(Permission.PROPERTY_UPDATE)
def unassign_manager(property_id: uuid.UUID, membership_id: uuid.UUID) -> None:
    service.unassign_manager(current_org_context(), property_id, membership_id)


@units_blp.get("")
@units_blp.arguments(UnitListQuerySchema, location="query")
@units_blp.response(200, UnitPageSchema)
@require_permission(Permission.UNIT_READ)
def list_units(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = service.list_units(
        current_org_context(),
        property_id=query["property_id"],
        building_id=query["building_id"],
        status=query["status"],
        limit=query["limit"],
        cursor=query["cursor"],
    )
    return {"items": items, "next_cursor": next_cursor}


@units_blp.post("")
@units_blp.arguments(UnitCreateSchema)
@units_blp.response(201, UnitSchema)
@require_permission(Permission.UNIT_CREATE)
def create_unit(payload: dict[str, Any]) -> Unit:
    return service.create_unit(current_org_context(), payload)


@units_blp.get("/<uuid:unit_id>")
@units_blp.response(200, UnitSchema)
@require_permission(Permission.UNIT_READ)
def get_unit(unit_id: uuid.UUID) -> Unit:
    return service.get_unit(current_org_context(), unit_id)


@units_blp.patch("/<uuid:unit_id>")
@units_blp.arguments(UnitUpdateSchema)
@units_blp.response(200, UnitSchema)
@require_permission(Permission.UNIT_UPDATE)
def update_unit(payload: dict[str, Any], unit_id: uuid.UUID) -> Unit:
    return service.update_unit(current_org_context(), unit_id, payload)
