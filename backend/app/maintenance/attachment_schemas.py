"""Attachment request/response schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.maintenance.images import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES


class AttachmentUploadRequestSchema(Schema):
    content_type = fields.String(
        required=True, validate=validate.OneOf(sorted(ALLOWED_CONTENT_TYPES))
    )
    size_bytes = fields.Integer(required=True, validate=validate.Range(min=1, max=MAX_UPLOAD_BYTES))


class AttachmentSchema(Schema):
    id = fields.UUID()
    status = fields.String()
    content_type = fields.String()
    size_bytes = fields.Integer(allow_none=True)
    width = fields.Integer(allow_none=True)
    height = fields.Integer(allow_none=True)
    uploaded_by_membership_id = fields.UUID()
    created_at = fields.DateTime()
    ready_at = fields.DateTime(allow_none=True)
    download_url = fields.String(allow_none=True)


class UploadInstructionsSchema(Schema):
    method = fields.String()
    url = fields.String()
    headers = fields.Dict(keys=fields.String(), values=fields.String())
    expires_in = fields.Integer()


class AttachmentUploadSchema(Schema):
    attachment = fields.Nested(AttachmentSchema)
    upload = fields.Nested(UploadInstructionsSchema)
