"""Maintenance request/response schemas. All free text is plain text (see plain_text)."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from marshmallow import Schema, fields, validate

from app.common.pagination import PageQuerySchema
from app.common.validation import not_blank, plain_text
from app.maintenance.models import MaintenanceCategory, MaintenancePriority, MaintenanceStatus


def _values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


Validator = Callable[[Any], Any]
TITLE: list[Validator] = [validate.Length(min=3, max=150), not_blank, plain_text]
DESCRIPTION: list[Validator] = [validate.Length(max=5000), not_blank, plain_text]
ACCESS_NOTES: list[Validator] = [validate.Length(max=1000), plain_text]


class MaintenanceCreateSchema(Schema):
    category = fields.String(required=True, validate=validate.OneOf(_values(MaintenanceCategory)))
    priority = fields.String(
        load_default=MaintenancePriority.NORMAL.value,
        validate=validate.OneOf(_values(MaintenancePriority)),
    )
    title = fields.String(required=True, validate=TITLE)
    description = fields.String(required=True, validate=DESCRIPTION)
    access_notes = fields.String(load_default=None, allow_none=True, validate=ACCESS_NOTES)
    # Staff only: tenants' location comes from their tenant profile.
    unit_id = fields.UUID(load_default=None)
    property_id = fields.UUID(load_default=None)


class MaintenanceUpdateSchema(Schema):
    version = fields.Integer(required=True, validate=validate.Range(min=1))
    category = fields.String(validate=validate.OneOf(_values(MaintenanceCategory)))
    priority = fields.String(validate=validate.OneOf(_values(MaintenancePriority)))
    title = fields.String(validate=TITLE)
    description = fields.String(validate=DESCRIPTION)
    access_notes = fields.String(allow_none=True, validate=ACCESS_NOTES)


class MaintenanceStatusChangeSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf(_values(MaintenanceStatus)))
    reason = fields.String(
        load_default=None, allow_none=True, validate=[validate.Length(max=1000), plain_text]
    )
    version = fields.Integer(required=True, validate=validate.Range(min=1))


class MaintenanceListQuerySchema(PageQuerySchema):
    status = fields.String(load_default=None, validate=validate.OneOf(_values(MaintenanceStatus)))
    priority = fields.String(
        load_default=None, validate=validate.OneOf(_values(MaintenancePriority))
    )
    property_id = fields.UUID(load_default=None)
    unit_id = fields.UUID(load_default=None)


class _PropertyRefSchema(Schema):
    id = fields.UUID()
    name = fields.String()


class _UnitRefSchema(Schema):
    id = fields.UUID()
    label = fields.String()


class _PersonRefSchema(Schema):
    membership_id = fields.UUID()
    full_name = fields.String()


class _AuthorSchema(_PersonRefSchema):
    role = fields.String()


class MaintenanceRequestSchema(Schema):
    id = fields.UUID()
    title = fields.String()
    description = fields.String()
    category = fields.String()
    priority = fields.String()
    status = fields.String()
    access_notes = fields.String(allow_none=True)
    property = fields.Nested(_PropertyRefSchema)
    unit = fields.Nested(_UnitRefSchema, allow_none=True)
    reported_by = fields.Nested(_PersonRefSchema)
    version = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    resolved_at = fields.DateTime(allow_none=True)
    closed_at = fields.DateTime(allow_none=True)
    allowed_transitions = fields.List(fields.String())  # present on single-request reads


class MaintenancePageSchema(Schema):
    items = fields.List(fields.Nested(MaintenanceRequestSchema))
    next_cursor = fields.String(allow_none=True)


class StatusHistorySchema(Schema):
    from_status = fields.String(allow_none=True)
    to_status = fields.String()
    reason = fields.String(allow_none=True)
    changed_by = fields.Nested(_PersonRefSchema)
    created_at = fields.DateTime()


class CommentCreateSchema(Schema):
    body = fields.String(required=True, validate=[validate.Length(max=5000), not_blank, plain_text])


class CommentSchema(Schema):
    id = fields.UUID()
    body = fields.String()
    author = fields.Nested(_AuthorSchema)
    created_at = fields.DateTime()


class CommentPageSchema(Schema):
    items = fields.List(fields.Nested(CommentSchema))
    next_cursor = fields.String(allow_none=True)
