from marshmallow import Schema, fields, validate

from app.organizations.models import MembershipRole


class ViewAsSchema(Schema):
    role = fields.String(
        required=True, validate=validate.OneOf([role.value for role in MembershipRole])
    )
