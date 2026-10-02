"""Import every module's models here so Alembic autogenerate and tests can see them."""

from app.audit.models import AuditLog
from app.auth.models import User, UserSession
from app.organizations.models import Invitation, Organization, OrganizationMembership
from app.properties.models import Building, Property, PropertyAssignment, Unit

__all__ = [
    "AuditLog",
    "Building",
    "Invitation",
    "Organization",
    "OrganizationMembership",
    "Property",
    "PropertyAssignment",
    "Unit",
    "User",
    "UserSession",
]
