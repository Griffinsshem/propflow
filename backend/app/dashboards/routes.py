"""Dashboard endpoints, one per spec dashboard page."""

from __future__ import annotations

from typing import Any

from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.dashboards import service
from app.dashboards.schemas import (
    ContractorDashboardSchema,
    OperationsDashboardSchema,
    OperationsQuerySchema,
    OrganizationDashboardSchema,
    TenantDashboardSchema,
)

blp = Blueprint("dashboards", __name__, url_prefix="/api/v1/dashboard", description="Dashboards.")


@blp.get("/operations")
@blp.arguments(OperationsQuerySchema, location="query")
@blp.response(200, OperationsDashboardSchema)
@require_permission(Permission.MAINTENANCE_ASSIGN)  # owners and managers
def operations(query: dict[str, Any]) -> dict[str, Any]:
    return service.operations(current_org_context(), property_id=query["property_id"])


@blp.get("/organization")
@blp.response(200, OrganizationDashboardSchema)
@require_permission(Permission.AUDIT_READ)  # owners
def organization() -> dict[str, Any]:
    return service.organization(current_org_context())


@blp.get("/tenant")
@blp.response(200, TenantDashboardSchema)
@require_permission(Permission.MAINTENANCE_CREATE)
def tenant() -> dict[str, Any]:
    return service.tenant(current_org_context())


@blp.get("/contractor")
@blp.response(200, ContractorDashboardSchema)
@require_permission(Permission.WORKORDER_UPDATE)
def contractor() -> dict[str, Any]:
    return service.contractor(current_org_context())
