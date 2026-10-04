from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.common.validation import not_blank
from app.organizations.models import MembershipRole

ROLE_VALUES = [role.value for role in MembershipRole]


class OrganizationSchema(Schema):
    id = fields.UUID()
    name = fields.String()
    status = fields.String()
    role = fields.String()
    created_at = fields.DateTime()


class OrganizationWriteSchema(Schema):
    """Only `name` is client-writable: status is never settable here (no self-unsuspend)."""

    name = fields.String(required=True, validate=[validate.Length(max=200), not_blank])


class InvitationCreateSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))
    role = fields.String(required=True, validate=validate.OneOf(ROLE_VALUES))


class InvitationSchema(Schema):
    id = fields.UUID()
    email = fields.Email()
    role = fields.String()
    unit_id = fields.UUID(allow_none=True)
    contractor_id = fields.UUID(allow_none=True)
    invited_by_user_id = fields.UUID()
    created_at = fields.DateTime()
    expires_at = fields.DateTime()
    accepted_at = fields.DateTime(allow_none=True)
    revoked_at = fields.DateTime(allow_none=True)


class InvitationPageSchema(Schema):
    items = fields.List(fields.Nested(InvitationSchema))
    next_cursor = fields.String(allow_none=True)


class InvitationTokenSchema(Schema):
    token = fields.String(required=True, validate=validate.Length(min=1, max=128))


class InvitationPreviewSchema(Schema):
    organization_name = fields.String()
    role = fields.String()
    email = fields.Email()
    expires_at = fields.DateTime()


class MemberSchema(Schema):
    id = fields.UUID()
    user_id = fields.UUID()
    full_name = fields.String()
    email = fields.Email()
    role = fields.String()
    status = fields.String()
    joined_at = fields.DateTime()


class MemberPageSchema(Schema):
    items = fields.List(fields.Nested(MemberSchema))
    next_cursor = fields.String(allow_none=True)


class MemberRoleUpdateSchema(Schema):
    role = fields.String(required=True, validate=validate.OneOf(ROLE_VALUES))
