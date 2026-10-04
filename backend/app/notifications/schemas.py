from __future__ import annotations

from marshmallow import Schema, fields

from app.common.pagination import PageQuerySchema


class NotificationListQuerySchema(PageQuerySchema):
    unread_only = fields.Boolean(load_default=False)


class NotificationSchema(Schema):
    id = fields.UUID()
    kind = fields.String()
    title = fields.String()
    body = fields.String()
    resource_type = fields.String()
    resource_id = fields.UUID()
    read = fields.Boolean()
    created_at = fields.DateTime()


class NotificationPageSchema(Schema):
    items = fields.List(fields.Nested(NotificationSchema))
    next_cursor = fields.String(allow_none=True)


class UnreadCountSchema(Schema):
    unread = fields.Integer()


class MarkedCountSchema(Schema):
    updated = fields.Integer()
