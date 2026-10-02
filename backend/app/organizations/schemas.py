from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.common.validation import not_blank


class OrganizationSchema(Schema):
    id = fields.UUID()
    name = fields.String()
    status = fields.String()
    role = fields.String()
    created_at = fields.DateTime()


class OrganizationWriteSchema(Schema):
    """Only `name` is client-writable: status is never settable here (no self-unsuspend)."""

    name = fields.String(required=True, validate=[validate.Length(max=200), not_blank])
