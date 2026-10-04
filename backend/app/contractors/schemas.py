"""Contractor request/response schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.common.pagination import PageQuerySchema
from app.common.validation import not_blank, plain_text
from app.contractors.models import ContractorSpecialty, ContractorStatus
from app.tenants.schemas import E164

SPECIALTIES = [s.value for s in ContractorSpecialty]
STATUSES = [s.value for s in ContractorStatus]


class ContractorCreateSchema(Schema):
    business_name = fields.String(
        required=True, validate=[validate.Length(max=200), not_blank, plain_text]
    )
    contact_name = fields.String(
        load_default=None, allow_none=True, validate=[validate.Length(max=200), plain_text]
    )
    phone = fields.String(load_default=None, allow_none=True, validate=E164)
    email = fields.Email(load_default=None, allow_none=True, validate=validate.Length(max=320))
    specialty = fields.String(required=True, validate=validate.OneOf(SPECIALTIES))


class ContractorUpdateSchema(Schema):
    version = fields.Integer(required=True, validate=validate.Range(min=1))
    business_name = fields.String(validate=[validate.Length(max=200), not_blank, plain_text])
    contact_name = fields.String(allow_none=True, validate=[validate.Length(max=200), plain_text])
    phone = fields.String(allow_none=True, validate=E164)
    email = fields.Email(allow_none=True, validate=validate.Length(max=320))
    specialty = fields.String(validate=validate.OneOf(SPECIALTIES))
    status = fields.String(validate=validate.OneOf(STATUSES))


class ContractorListQuerySchema(PageQuerySchema):
    status = fields.String(load_default=None, validate=validate.OneOf(STATUSES))
    specialty = fields.String(load_default=None, validate=validate.OneOf(SPECIALTIES))


class ContractorInviteSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))


class ContractorSchema(Schema):
    id = fields.UUID()
    business_name = fields.String()
    contact_name = fields.String(allow_none=True)
    phone = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    specialty = fields.String()
    status = fields.String()
    has_login = fields.Boolean()
    version = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class ContractorPageSchema(Schema):
    items = fields.List(fields.Nested(ContractorSchema))
    next_cursor = fields.String(allow_none=True)
