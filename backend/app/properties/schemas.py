"""Request/response schemas. Unknown fields such as organization_id are rejected."""

from __future__ import annotations

from enum import StrEnum

from marshmallow import Schema, fields, validate

from app.common.pagination import PageQuerySchema
from app.common.validation import not_blank
from app.properties.models import PropertyStatus, PropertyType, UnitStatus


def _values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


COUNTRY_CODE = validate.Regexp(r"^[A-Z]{2}$", error="Use a two-letter ISO code, e.g. KE.")
FLOOR_RANGE = validate.Range(min=-5, max=300)
BEDROOM_RANGE = validate.Range(min=0, max=50)


class PropertySchema(Schema):
    id = fields.UUID()
    name = fields.String()
    property_type = fields.String()
    status = fields.String()
    address_line = fields.String()
    city = fields.String()
    region = fields.String(allow_none=True)
    country_code = fields.String()
    description = fields.String(allow_none=True)
    version = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class PropertyCreateSchema(Schema):
    name = fields.String(required=True, validate=[validate.Length(max=200), not_blank])
    property_type = fields.String(required=True, validate=validate.OneOf(_values(PropertyType)))
    address_line = fields.String(required=True, validate=[validate.Length(max=200), not_blank])
    city = fields.String(required=True, validate=[validate.Length(max=100), not_blank])
    region = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    country_code = fields.String(load_default="KE", validate=COUNTRY_CODE)
    description = fields.String(
        load_default=None, allow_none=True, validate=validate.Length(max=2000)
    )


class PropertyUpdateSchema(Schema):
    version = fields.Integer(required=True, validate=validate.Range(min=1))
    name = fields.String(validate=[validate.Length(max=200), not_blank])
    property_type = fields.String(validate=validate.OneOf(_values(PropertyType)))
    status = fields.String(validate=validate.OneOf(_values(PropertyStatus)))
    address_line = fields.String(validate=[validate.Length(max=200), not_blank])
    city = fields.String(validate=[validate.Length(max=100), not_blank])
    region = fields.String(allow_none=True, validate=validate.Length(max=100))
    country_code = fields.String(validate=COUNTRY_CODE)
    description = fields.String(allow_none=True, validate=validate.Length(max=2000))


class PropertyListQuerySchema(PageQuerySchema):
    status = fields.String(
        load_default=PropertyStatus.ACTIVE.value,
        validate=validate.OneOf(_values(PropertyStatus)),
    )


class PropertyPageSchema(Schema):
    items = fields.List(fields.Nested(PropertySchema))
    next_cursor = fields.String(allow_none=True)


class BuildingSchema(Schema):
    id = fields.UUID()
    property_id = fields.UUID()
    name = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class BuildingWriteSchema(Schema):
    name = fields.String(required=True, validate=[validate.Length(max=100), not_blank])


class UnitSchema(Schema):
    id = fields.UUID()
    property_id = fields.UUID()
    building_id = fields.UUID(allow_none=True)
    label = fields.String()
    floor = fields.Integer(allow_none=True)
    bedrooms = fields.Integer(allow_none=True)
    status = fields.String()
    version = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class UnitCreateSchema(Schema):
    property_id = fields.UUID(required=True)
    building_id = fields.UUID(load_default=None, allow_none=True)
    label = fields.String(required=True, validate=[validate.Length(max=50), not_blank])
    floor = fields.Integer(load_default=None, allow_none=True, validate=FLOOR_RANGE)
    bedrooms = fields.Integer(load_default=None, allow_none=True, validate=BEDROOM_RANGE)
    status = fields.String(
        load_default=UnitStatus.VACANT.value, validate=validate.OneOf(_values(UnitStatus))
    )


class UnitUpdateSchema(Schema):
    version = fields.Integer(required=True, validate=validate.Range(min=1))
    building_id = fields.UUID(allow_none=True)
    label = fields.String(validate=[validate.Length(max=50), not_blank])
    floor = fields.Integer(allow_none=True, validate=FLOOR_RANGE)
    bedrooms = fields.Integer(allow_none=True, validate=BEDROOM_RANGE)
    status = fields.String(validate=validate.OneOf(_values(UnitStatus)))


class UnitListQuerySchema(PageQuerySchema):
    property_id = fields.UUID(load_default=None)
    building_id = fields.UUID(load_default=None)
    status = fields.String(load_default=None, validate=validate.OneOf(_values(UnitStatus)))


class UnitPageSchema(Schema):
    items = fields.List(fields.Nested(UnitSchema))
    next_cursor = fields.String(allow_none=True)


class ManagerAssignSchema(Schema):
    membership_id = fields.UUID(required=True)


class PropertyManagerSchema(Schema):
    membership_id = fields.UUID()
    user_id = fields.UUID()
    full_name = fields.String()
    email = fields.Email()
    assigned_at = fields.DateTime()
