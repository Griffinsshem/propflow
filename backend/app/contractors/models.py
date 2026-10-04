"""Contractor records (spec 3.8): the businesses that do the work.

A record can be linked to a contractor login (membership) through an invitation, so that
person can see and update their own work orders. Not a marketplace: no bids, ratings or pay.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin, UUIDPrimaryKeyMixin, enum_values_check
from app.extensions import Base


class ContractorSpecialty(StrEnum):
    GENERAL = "general"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    CARPENTRY = "carpentry"
    CLEANING = "cleaning"
    SECURITY = "security"
    HVAC = "hvac"
    PAINTING = "painting"


class ContractorStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Contractor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contractors"
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),  # target of child composite FKs
        UniqueConstraint("organization_id", "business_name"),
        UniqueConstraint("membership_id"),  # one login represents at most one contractor
        ForeignKeyConstraint(
            ["membership_id", "organization_id"],
            ["organization_memberships.id", "organization_memberships.organization_id"],
            ondelete="RESTRICT",
            name="fk_contractors_membership",
        ),
        CheckConstraint("char_length(btrim(business_name)) > 0", name="name_not_blank"),
        CheckConstraint(
            enum_values_check("specialty", ContractorSpecialty), name="specialty_valid"
        ),
        CheckConstraint(enum_values_check("status", ContractorStatus), name="status_valid"),
        CheckConstraint(r"phone IS NULL OR phone ~ '^\+[1-9][0-9]{7,14}$'", name="phone_e164"),
        CheckConstraint("email IS NULL OR email = lower(email)", name="email_lowercase"),
        Index("ix_contractors_org_created", "organization_id", "created_at", "id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    business_name: Mapped[str] = mapped_column(String(200))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(16))
    email: Mapped[str | None] = mapped_column(String(320))
    specialty: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), default=ContractorStatus.ACTIVE, server_default=ContractorStatus.ACTIVE
    )
    membership_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:
        return f"<Contractor {self.id}>"
