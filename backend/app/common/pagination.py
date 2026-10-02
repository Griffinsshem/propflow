"""Keyset (cursor) pagination: stable under concurrent inserts, constant cost at any depth."""

from __future__ import annotations

import base64
import binascii
import uuid
from datetime import datetime

from marshmallow import Schema, fields, validate

from app.common.errors import RequestValidationError

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class PageQuerySchema(Schema):
    limit = fields.Integer(
        load_default=DEFAULT_PAGE_SIZE, validate=validate.Range(min=1, max=MAX_PAGE_SIZE)
    )
    cursor = fields.String(load_default=None, validate=validate.Length(max=200))


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """A tampered cursor can only move within the caller's already-scoped query."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_part, id_part = raw.split("|", 1)
        created_at = datetime.fromisoformat(created_part)
        row_id = uuid.UUID(id_part)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise RequestValidationError("Invalid pagination cursor.") from exc
    if created_at.tzinfo is None:
        raise RequestValidationError("Invalid pagination cursor.")
    return created_at, row_id
