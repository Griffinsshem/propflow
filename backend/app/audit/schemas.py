from __future__ import annotations

from marshmallow import Schema, fields


class AuditLogEntrySchema(Schema):
    id = fields.UUID()
    action = fields.String()
    resource_type = fields.String()
    resource_id = fields.UUID(allow_none=True)
    actor_user_id = fields.UUID(allow_none=True)
    request_id = fields.String(allow_none=True)
    details = fields.Dict()
    created_at = fields.DateTime()


class AuditLogPageSchema(Schema):
    items = fields.List(fields.Nested(AuditLogEntrySchema))
    next_cursor = fields.String(allow_none=True)
