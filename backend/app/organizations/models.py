"""Tenancy models: organizations, memberships and invitations."""

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
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin, UUIDPrimaryKeyMixin, enum_values_check
from app.extensions import Base


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class MembershipRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    TENANT = "tenant"
    CONTRACTOR = "contractor"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("char_length(btrim(name)) > 0", name="name_not_blank"),
        CheckConstraint(enum_values_check("status", OrganizationStatus), name="status_valid"),
    )

    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20), default=OrganizationStatus.ACTIVE, server_default=OrganizationStatus.ACTIVE
    )

    def __repr__(self) -> str:
        return f"<Organization {self.id}>"


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's single role within one organization."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        UniqueConstraint("id", "organization_id"),  # composite-FK target for tenant integrity
        CheckConstraint(enum_values_check("role", MembershipRole), name="role_valid"),
        CheckConstraint(enum_values_check("status", MembershipStatus), name="status_valid"),
        # (organization_id, ...) lookups use the unique constraint's index; this serves "my orgs".
        Index("ix_organization_memberships_user_id", "user_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), default=MembershipStatus.ACTIVE, server_default=MembershipStatus.ACTIVE
    )

    def __repr__(self) -> str:
        return f"<OrganizationMembership {self.id} role={self.role}>"


class Invitation(UUIDPrimaryKeyMixin, Base):
    """Invite to join an organization. Only the SHA-256 hash of the emailed token is stored."""

    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint(enum_values_check("role", MembershipRole), name="role_valid"),
        CheckConstraint("char_length(token_hash) = 64", name="token_hash_length"),
        CheckConstraint("unit_id IS NULL OR role = 'tenant'", name="unit_only_for_tenants"),
        ForeignKeyConstraint(
            ["unit_id", "organization_id"],
            ["units.id", "units.organization_id"],
            ondelete="RESTRICT",
            name="fk_invitations_unit",
        ),
        CheckConstraint(
            "contractor_id IS NULL OR role = 'contractor'", name="contractor_only_for_contractors"
        ),
        ForeignKeyConstraint(
            ["contractor_id", "organization_id"],
            ["contractors.id", "contractors.organization_id"],
            ondelete="RESTRICT",
            name="fk_invitations_contractor",
        ),
        CheckConstraint("expires_at > created_at", name="expires_after_created"),
        CheckConstraint(
            "accepted_at IS NULL OR revoked_at IS NULL", name="not_accepted_and_revoked"
        ),
        CheckConstraint(
            "(accepted_at IS NULL) = (accepted_by_user_id IS NULL)", name="acceptance_consistent"
        ),
        # At most one pending invitation per email per organization.
        Index(
            "uq_invitations_pending_org_email",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(20))
    # Tenant invitations carry the unit the tenant will occupy on acceptance.
    unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    # Contractor invitations can link the new login to a contractor record.
    contractor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Invitation {self.id} role={self.role}>"
