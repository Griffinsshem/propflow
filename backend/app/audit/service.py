"""Audit trail. Entries join the caller's transaction: they commit or roll back with the change."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g, has_request_context, request
from sqlalchemy import select, tuple_

from app.audit.models import AuditLog
from app.common.pagination import decode_cursor, encode_cursor
from app.extensions import db

# Detail keys containing any of these are dropped: secrets never enter the audit trail.
_SENSITIVE_KEY_FRAGMENTS = ("password", "token", "secret", "hash", "cookie")


def _scrub(details: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in details.items()
        if not any(fragment in key.lower() for fragment in _SENSITIVE_KEY_FRAGMENTS)
    }


def record(
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    *,
    organization_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    if actor_user_id is None:
        user = g.get("current_user")
        actor_user_id = user.id if user is not None else None
    entry = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=g.get("request_id"),
        ip_address=request.remote_addr if has_request_context() else None,
        details=_scrub(details or {}),
    )
    db.session.add(entry)
    return entry


def list_for_organization(
    organization_id: uuid.UUID, *, limit: int, cursor: str | None
) -> tuple[list[AuditLog], str | None]:
    stmt = select(AuditLog).where(AuditLog.organization_id == organization_id)
    if cursor:
        created_at, entry_id = decode_cursor(cursor)
        stmt = stmt.where(tuple_(AuditLog.created_at, AuditLog.id) < tuple_(created_at, entry_id))
    stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit + 1)
    rows = list(db.session.execute(stmt).scalars())
    page = rows[:limit]
    next_cursor = encode_cursor(page[-1].created_at, page[-1].id) if len(rows) > limit else None
    return page, next_cursor
