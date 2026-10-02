"""Reusable marshmallow validators."""

from __future__ import annotations

import re

from marshmallow import ValidationError

# C0 control characters except tab, newline and carriage return, plus DEL.
# NUL in particular would make PostgreSQL reject the value with a server error.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def not_blank(value: str) -> None:
    if not value.strip():
        raise ValidationError("Must not be blank.")


def plain_text(value: str) -> None:
    """Text is stored verbatim and escaped on output; only control characters are refused."""
    if _CONTROL_CHARACTERS.search(value):
        raise ValidationError("Contains unsupported control characters.")
