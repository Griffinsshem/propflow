"""Append-only audit trail. UPDATE/DELETE are blocked by a database trigger (see migrations)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import UUIDPrimaryKeyMixin
from app.extensions import Base


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(r"action ~ '^[a-z_]+(\.[a-z_]+)+$'", name="action_format"),
        CheckConstraint("char_length(resource_type) > 0", name="resource_type_not_blank"),
        # Serves the org audit listing: WHERE organization_id = ? ORDER BY created_at, id.
        Index("ix_audit_logs_org_created", "organization_id", "created_at", "id"),
    )

    # NULL for account-level events (e.g. password reset) that belong to no organization.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    request_id: Mapped[str | None] = mapped_column(String(128))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} {self.action}>"
