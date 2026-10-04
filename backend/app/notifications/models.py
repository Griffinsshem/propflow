"""In-app notifications, written in the same transaction as the event that causes them."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import UUIDPrimaryKeyMixin, enum_values_check
from app.extensions import Base


class NotificationKind(StrEnum):
    REQUEST_SUBMITTED = "request_submitted"
    REQUEST_STATUS_CHANGED = "request_status_changed"
    REQUEST_COMMENTED = "request_commented"
    WORK_ORDER_ASSIGNED = "work_order_assigned"
    WORK_ORDER_STATUS_CHANGED = "work_order_status_changed"


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recipient_membership_id", "organization_id"],
            ["organization_memberships.id", "organization_memberships.organization_id"],
            ondelete="RESTRICT",
            name="fk_notifications_recipient",
        ),
        CheckConstraint(enum_values_check("kind", NotificationKind), name="kind_valid"),
        Index("ix_notifications_recipient_created", "recipient_membership_id", "created_at", "id"),
        # Serves the unread badge count without scanning read history.
        Index(
            "ix_notifications_recipient_unread",
            "recipient_membership_id",
            postgresql_where=text("read_at IS NULL"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    recipient_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(150))
    body: Mapped[str] = mapped_column(String(500))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
