"""Import every module's models here so Alembic autogenerate and tests can see them."""

from app.audit.models import AuditLog
from app.auth.models import User, UserSession
from app.contractors.models import Contractor
from app.maintenance.models import (
    MaintenanceAttachment,
    MaintenanceComment,
    MaintenanceRequest,
    MaintenanceStatusHistory,
)
from app.notifications.models import Notification
from app.organizations.models import Invitation, Organization, OrganizationMembership
from app.properties.models import Building, Property, PropertyAssignment, Unit
from app.tenants.models import TenantProfile
from app.work_orders.models import WorkOrder, WorkOrderStatusHistory

__all__ = [
    "AuditLog",
    "Building",
    "Contractor",
    "Invitation",
    "MaintenanceAttachment",
    "MaintenanceComment",
    "MaintenanceRequest",
    "MaintenanceStatusHistory",
    "Notification",
    "Organization",
    "OrganizationMembership",
    "Property",
    "PropertyAssignment",
    "TenantProfile",
    "Unit",
    "User",
    "UserSession",
    "WorkOrder",
    "WorkOrderStatusHistory",
]
