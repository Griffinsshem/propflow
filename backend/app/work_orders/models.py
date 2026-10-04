"""Work orders (spec 3.9): the contractor-facing side of a maintenance request."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin, UUIDPrimaryKeyMixin, enum_values_check
from app.extensions import Base
from app.maintenance.models import MaintenancePriority


class WorkOrderStatus(StrEnum):
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = frozenset(
    {WorkOrderStatus.ASSIGNED, WorkOrderStatus.ACCEPTED, WorkOrderStatus.IN_PROGRESS}
)
# Contractors keep seeing finished work; declined and cancelled orders drop out of view.
CONTRACTOR_VISIBLE_STATUSES = ACTIVE_STATUSES | {WorkOrderStatus.COMPLETED}

_MEMBERSHIP_KEY = ["organization_memberships.id", "organization_memberships.organization_id"]


class WorkOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),  # target of the history composite FK
        ForeignKeyConstraint(
            ["request_id", "organization_id"],
            ["maintenance_requests.id", "maintenance_requests.organization_id"],
            ondelete="RESTRICT",
            name="fk_work_orders_request",
        ),
        ForeignKeyConstraint(
            ["contractor_id", "organization_id"],
            ["contractors.id", "contractors.organization_id"],
            ondelete="RESTRICT",
            name="fk_work_orders_contractor",
        ),
        ForeignKeyConstraint(
            ["created_by_membership_id", "organization_id"],
            _MEMBERSHIP_KEY,
            ondelete="RESTRICT",
            name="fk_work_orders_creator",
        ),
        CheckConstraint(enum_values_check("status", WorkOrderStatus), name="status_valid"),
        CheckConstraint(enum_values_check("priority", MaintenancePriority), name="priority_valid"),
        CheckConstraint("char_length(description) <= 2000", name="description_length"),
        # At most one active work order per maintenance request.
        Index(
            "uq_work_orders_one_active_per_request",
            "request_id",
            unique=True,
            postgresql_where=text("status IN ('assigned', 'accepted', 'in_progress')"),
        ),
        Index("ix_work_orders_org_created", "organization_id", "created_at", "id"),
        Index("ix_work_orders_contractor_status", "organization_id", "contractor_id", "status"),
        Index("ix_work_orders_request", "organization_id", "request_id"),
        # Serves overdue and upcoming work orders (active ones only).
        Index(
            "ix_work_orders_active_due",
            "organization_id",
            "due_date",
            postgresql_where=text("status IN ('assigned', 'accepted', 'in_progress')"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    contractor_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(20))
    priority: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:
        return f"<WorkOrder {self.id} {self.status}>"


class WorkOrderStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "work_order_status_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["work_order_id", "organization_id"],
            ["work_orders.id", "work_orders.organization_id"],
            ondelete="RESTRICT",
            name="fk_work_order_status_history_order",
        ),
        ForeignKeyConstraint(
            ["changed_by_membership_id", "organization_id"],
            _MEMBERSHIP_KEY,
            ondelete="RESTRICT",
            name="fk_work_order_status_history_actor",
        ),
        CheckConstraint(enum_values_check("from_status", WorkOrderStatus), name="from_valid"),
        CheckConstraint(enum_values_check("to_status", WorkOrderStatus), name="to_valid"),
        CheckConstraint("char_length(reason) <= 1000", name="reason_length"),
        Index("ix_work_order_status_history_order", "work_order_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    changed_by_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
