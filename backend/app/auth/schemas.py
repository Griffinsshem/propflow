"""Request/response schemas. Unknown fields are rejected (marshmallow default: RAISE)."""

from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate


def _not_blank(value: str) -> None:
    if not value.strip():
        raise ValidationError("Must not be blank.")


class RegisterSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))
    # 12+ characters, no composition rules (NIST SP 800-63B). The upper bound limits hashing cost.
    password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=12, max=128)
    )
    full_name = fields.String(required=True, validate=[validate.Length(max=200), _not_blank])


class LoginSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))
    password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=1, max=128)
    )


class MembershipSummarySchema(Schema):
    organization_id = fields.UUID()
    organization_name = fields.String()
    role = fields.String()


class CurrentUserSchema(Schema):
    id = fields.UUID()
    email = fields.Email()
    full_name = fields.String()
    email_verified = fields.Boolean()
    active_organization_id = fields.UUID(allow_none=True)
    is_demo = fields.Boolean()
    demo_expires_at = fields.DateTime(allow_none=True)
    memberships = fields.List(fields.Nested(MembershipSummarySchema))


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))


class ResetPasswordSchema(Schema):
    token = fields.String(required=True, validate=validate.Length(min=1, max=512))
    new_password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=12, max=128)
    )


class EmailTokenSchema(Schema):
    token = fields.String(required=True, validate=validate.Length(min=1, max=512))


class MessageSchema(Schema):
    message = fields.String()
