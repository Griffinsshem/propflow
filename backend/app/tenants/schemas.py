"""Tenant request/response schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.common.pagination import PageQuerySchema
from app.organizations.models import MembershipStatus

E164 = validate.Regexp(
    r"^\+[1-9][0-9]{7,14}$", error="Use international format, e.g. +254712345678."
)


class TenantUnitSchema(Schema):
    id = fields.UUID()
    label = fields.String()
    building_id = fields.UUID(allow_none=True)
    property_id = fields.UUID()
    property_name = fields.String(allow_none=True)


class TenantSchema(Schema):
    id = fields.UUID()
    membership_id = fields.UUID()
    user_id = fields.UUID()
    full_name = fields.String()
    email = fields.Email()
    phone = fields.String(allow_none=True)
    status = fields.String()
    move_in_date = fields.Date(allow_none=True)
    version = fields.Integer()
    unit = fields.Nested(TenantUnitSchema, allow_none=True)


class TenantPageSchema(Schema):
    items = fields.List(fields.Nested(TenantSchema))
    next_cursor = fields.String(allow_none=True)


class TenantInviteSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))
    unit_id = fields.UUID(required=True)


class TenantUpdateSchema(Schema):
    version = fields.Integer(required=True, validate=validate.Range(min=1))
    unit_id = fields.UUID(allow_none=True)
    phone = fields.String(allow_none=True, validate=E164)
    move_in_date = fields.Date(allow_none=True)


class TenantListQuerySchema(PageQuerySchema):
    status = fields.String(
        load_default=MembershipStatus.ACTIVE.value,
        validate=validate.OneOf([s.value for s in MembershipStatus]),
    )
    unit_id = fields.UUID(load_default=None)
    property_id = fields.UUID(load_default=None)
