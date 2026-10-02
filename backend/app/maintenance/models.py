"""Maintenance requests, their status history and comments (spec 3.4-3.6)."""

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
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin, UUIDPrimaryKeyMixin, enum_values_check
from app.extensions import Base


class MaintenanceCategory(StrEnum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    WATER = "water"
    HEATING_COOLING = "heating_cooling"
    APPLIANCE = "appliance"
    SECURITY = "security"
    STRUCTURAL = "structural"
    CLEANING = "cleaning"
    OTHER = "other"


class MaintenancePriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MaintenanceStatus(StrEnum):
    SUBMITTED = "submitted"
    TRIAGED = "triaged"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


_MEMBERSHIP_KEY = ["organization_memberships.id", "organization_memberships.organization_id"]


class MaintenanceRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_requests"
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),  # target of child composite FKs
        ForeignKeyConstraint(
            ["property_id", "organization_id"],
            ["properties.id", "properties.organization_id"],
            ondelete="RESTRICT",
            name="fk_maintenance_requests_property",
        ),
        # The unit (if any) must belong to the request's property.
        ForeignKeyConstraint(
            ["unit_id", "property_id"],
            ["units.id", "units.property_id"],
            ondelete="RESTRICT",
            name="fk_maintenance_requests_unit",
        ),
        ForeignKeyConstraint(
            ["reported_by_membership_id", "organization_id"],
            _MEMBERSHIP_KEY,
            ondelete="RESTRICT",
            name="fk_maintenance_requests_reporter",
        ),
        CheckConstraint(enum_values_check("category", MaintenanceCategory), name="category_valid"),
        CheckConstraint(enum_values_check("priority", MaintenancePriority), name="priority_valid"),
        CheckConstraint(enum_values_check("status", MaintenanceStatus), name="status_valid"),
        CheckConstraint("char_length(btrim(title)) > 0", name="title_not_blank"),
        CheckConstraint("char_length(description) <= 5000", name="description_length"),
        CheckConstraint("char_length(access_notes) <= 1000", name="access_notes_length"),
        Index("ix_maintenance_requests_org_created", "organization_id", "created_at", "id"),
        Index("ix_maintenance_requests_org_status", "organization_id", "status"),
        Index(
            "ix_maintenance_requests_property_status", "organization_id", "property_id", "status"
        ),
        Index("ix_maintenance_requests_reporter", "organization_id", "reported_by_membership_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    property_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    reported_by_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    category: Mapped[str] = mapped_column(String(30))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    access_notes: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:
        return f"<MaintenanceRequest {self.id} {self.status}>"


class MaintenanceStatusHistory(UUIDPrimaryKeyMixin, Base):
    """One row per status change, written in the same transaction as the change."""

    __tablename__ = "maintenance_status_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["request_id", "organization_id"],
            ["maintenance_requests.id", "maintenance_requests.organization_id"],
            ondelete="RESTRICT",
            name="fk_maintenance_status_history_request",
        ),
        ForeignKeyConstraint(
            ["changed_by_membership_id", "organization_id"],
            _MEMBERSHIP_KEY,
            ondelete="RESTRICT",
            name="fk_maintenance_status_history_actor",
        ),
        CheckConstraint(enum_values_check("from_status", MaintenanceStatus), name="from_valid"),
        CheckConstraint(enum_values_check("to_status", MaintenanceStatus), name="to_valid"),
        CheckConstraint("char_length(reason) <= 1000", name="reason_length"),
        Index("ix_maintenance_status_history_request", "request_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    from_status: Mapped[str | None] = mapped_column(String(20))  # NULL for the initial submit
    to_status: Mapped[str] = mapped_column(String(20))
    changed_by_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceComment(UUIDPrimaryKeyMixin, Base):
    """Plain text, immutable once posted (no edits in the MVP: the thread is a record)."""

    __tablename__ = "maintenance_comments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["request_id", "organization_id"],
            ["maintenance_requests.id", "maintenance_requests.organization_id"],
            ondelete="RESTRICT",
            name="fk_maintenance_comments_request",
        ),
        ForeignKeyConstraint(
            ["author_membership_id", "organization_id"],
            _MEMBERSHIP_KEY,
            ondelete="RESTRICT",
            name="fk_maintenance_comments_author",
        ),
        CheckConstraint("char_length(btrim(body)) > 0", name="body_not_blank"),
        CheckConstraint("char_length(body) <= 5000", name="body_length"),
        Index("ix_maintenance_comments_request", "request_id", "created_at", "id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    author_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
