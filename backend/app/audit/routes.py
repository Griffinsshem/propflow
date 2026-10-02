"""Organization audit trail (owners only)."""

from __future__ import annotations

from typing import Any

from flask_smorest import Blueprint

from app.audit import service
from app.audit.schemas import AuditLogPageSchema
from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.common.pagination import PageQuerySchema

blp = Blueprint("audit", __name__, url_prefix="/api/v1/audit-log", description="Audit trail.")


@blp.get("")
@blp.arguments(PageQuerySchema, location="query")
@blp.response(200, AuditLogPageSchema)
@require_permission(Permission.AUDIT_READ)
def list_audit_log(query: dict[str, Any]) -> dict[str, Any]:
    context = current_org_context()
    items, next_cursor = service.list_for_organization(
        context.organization_id, limit=query["limit"], cursor=query["cursor"]
    )
    return {"items": items, "next_cursor": next_cursor}
