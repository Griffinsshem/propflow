"""Property hierarchy: Organization -> Property -> optional Building -> Unit.

Composite foreign keys carry organization_id down the hierarchy, so the database itself
guarantees a building, unit or manager assignment can never point at another
organization's property or membership: tenant isolation enforced below the application.
"""

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
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin, UUIDPrimaryKeyMixin, enum_values_check
from app.extensions import Base


class PropertyType(StrEnum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    MIXED_USE = "mixed_use"
    ESTATE = "estate"


class PropertyStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class UnitStatus(StrEnum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    UNAVAILABLE = "unavailable"


class Property(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "properties"
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),  # target of child composite FKs
        CheckConstraint("char_length(btrim(name)) > 0", name="name_not_blank"),
        CheckConstraint(enum_values_check("property_type", PropertyType), name="type_valid"),
        CheckConstraint(enum_values_check("status", PropertyStatus), name="status_valid"),
        CheckConstraint("country_code ~ '^[A-Z]{2}$'", name="country_code_format"),
        CheckConstraint("char_length(description) <= 2000", name="description_length"),
        Index("ix_properties_org_created", "organization_id", "created_at", "id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(200))
    property_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), default=PropertyStatus.ACTIVE, server_default=PropertyStatus.ACTIVE
    )
    address_line: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(2), default="KE", server_default="KE")
    description: Mapped[str | None] = mapped_column(Text)
    # Optimistic concurrency: UPDATE ... WHERE version = <loaded version>.
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:
        return f"<Property {self.id}>"


class Building(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "buildings"
    __table_args__ = (
        UniqueConstraint("id", "property_id"),  # target of the unit -> building composite FK
        UniqueConstraint("property_id", "name"),
        ForeignKeyConstraint(
            ["property_id", "organization_id"],
            ["properties.id", "properties.organization_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("char_length(btrim(name)) > 0", name="name_not_blank"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    property_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(String(100))

    def __repr__(self) -> str:
        return f"<Building {self.id}>"


class Unit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("property_id", "label"),
        UniqueConstraint("id", "organization_id"),  # composite-FK target for tenant integrity
        ForeignKeyConstraint(
            ["property_id", "organization_id"],
            ["properties.id", "properties.organization_id"],
            ondelete="RESTRICT",
        ),
        # A unit's building must belong to the unit's own property (NULL = no building).
        ForeignKeyConstraint(
            ["building_id", "property_id"],
            ["buildings.id", "buildings.property_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("char_length(btrim(label)) > 0", name="label_not_blank"),
        CheckConstraint(enum_values_check("status", UnitStatus), name="status_valid"),
        CheckConstraint("bedrooms IS NULL OR bedrooms >= 0", name="bedrooms_non_negative"),
        Index("ix_units_org_created", "organization_id", "created_at", "id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    property_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    building_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    label: Mapped[str] = mapped_column(String(50))
    floor: Mapped[int | None] = mapped_column(SmallInteger)
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(
        String(20), default=UnitStatus.VACANT, server_default=UnitStatus.VACANT
    )
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:
        return f"<Unit {self.id}>"


class PropertyAssignment(UUIDPrimaryKeyMixin, Base):
    """A manager responsible for a property. Managers only see their assigned properties."""

    __tablename__ = "property_assignments"
    __table_args__ = (
        UniqueConstraint("property_id", "membership_id"),
        # CASCADE (unlike the RESTRICT default): an assignment is not business history and must
        # not block deleting an empty property. The audit log keeps the record.
        ForeignKeyConstraint(
            ["property_id", "organization_id"],
            ["properties.id", "properties.organization_id"],
            ondelete="CASCADE",
            name="fk_property_assignments_property",
        ),
        ForeignKeyConstraint(
            ["membership_id", "organization_id"],
            ["organization_memberships.id", "organization_memberships.organization_id"],
            ondelete="CASCADE",
            name="fk_property_assignments_membership",
        ),
        Index("ix_property_assignments_membership", "organization_id", "membership_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    property_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
