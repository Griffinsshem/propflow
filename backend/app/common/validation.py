"""Reusable marshmallow validators."""

from __future__ import annotations

from marshmallow import ValidationError


def not_blank(value: str) -> None:
    if not value.strip():
        raise ValidationError("Must not be blank.")
