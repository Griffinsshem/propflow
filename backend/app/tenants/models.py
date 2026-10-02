"""Tenant profiles: a tenant membership's contact details and the unit they occupy.

Deliberately small (spec 3.3: not a CRM). Leases arrive in V2.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import Base


class TenantProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenant_profiles"
    __table_args__ = (
        UniqueConstraint("membership_id"),
        ForeignKeyConstraint(
            ["membership_id", "organization_id"],
            ["organization_memberships.id", "organization_memberships.organization_id"],
            ondelete="RESTRICT",
            name="fk_tenant_profiles_membership",
        ),
        ForeignKeyConstraint(
            ["unit_id", "organization_id"],
            ["units.id", "units.organization_id"],
            ondelete="RESTRICT",
            name="fk_tenant_profiles_unit",
        ),
        CheckConstraint(r"phone IS NULL OR phone ~ '^\+[1-9][0-9]{7,14}$'", name="phone_e164"),
        Index("ix_tenant_profiles_unit", "organization_id", "unit_id"),
        Index("ix_tenant_profiles_org_created", "organization_id", "created_at", "id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    phone: Mapped[str | None] = mapped_column(String(16))
    move_in_date: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:
        return f"<TenantProfile {self.id}>"
