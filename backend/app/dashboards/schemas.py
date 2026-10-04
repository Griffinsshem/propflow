"""Dashboard response schemas: explicit counters so the OpenAPI contract is precise."""

from __future__ import annotations

from marshmallow import Schema, fields

from app.audit.schemas import AuditLogEntrySchema
from app.maintenance.schemas import MaintenanceRequestSchema
from app.notifications.schemas import NotificationSchema
from app.tenants.schemas import TenantUnitSchema
from app.work_orders.schemas import WorkOrderSchema


class OperationsQuerySchema(Schema):
    property_id = fields.UUID(load_default=None)


class RequestCountsSchema(Schema):
    open = fields.Integer()
    new = fields.Integer()
    urgent = fields.Integer()
    in_flight = fields.Integer()
    in_progress = fields.Integer()
    waiting = fields.Integer()
    resolved = fields.Integer()
    closed = fields.Integer()
    resolved_this_month = fields.Integer()


class WorkOrderCountsSchema(Schema):
    awaiting_acceptance = fields.Integer()
    accepted = fields.Integer()
    in_progress = fields.Integer()
    active = fields.Integer()
    overdue = fields.Integer()
    completed_this_month = fields.Integer()


class OperationsDashboardSchema(Schema):
    requests = fields.Nested(RequestCountsSchema)
    work_orders = fields.Nested(WorkOrderCountsSchema)
    recent_requests = fields.List(fields.Nested(MaintenanceRequestSchema))
    recently_updated = fields.List(fields.Nested(MaintenanceRequestSchema))
    overdue_work_orders = fields.List(fields.Nested(WorkOrderSchema))


class OrganizationCountsSchema(Schema):
    properties = fields.Integer()
    units = fields.Integer()
    active_tenants = fields.Integer()
    open_requests = fields.Integer()
    active_work_orders = fields.Integer()


class OrganizationDashboardSchema(Schema):
    counts = fields.Nested(OrganizationCountsSchema)
    recent_activity = fields.List(fields.Nested(AuditLogEntrySchema))


class TenantRequestCountsSchema(Schema):
    submitted = fields.Integer()
    in_progress = fields.Integer()
    waiting = fields.Integer()
    resolved = fields.Integer()
    closed = fields.Integer()


class TenantDashboardSchema(Schema):
    unit = fields.Nested(TenantUnitSchema, allow_none=True)
    requests = fields.Nested(TenantRequestCountsSchema)
    recent_requests = fields.List(fields.Nested(MaintenanceRequestSchema))
    recent_activity = fields.List(fields.Nested(NotificationSchema))


class ContractorDashboardSchema(Schema):
    work_orders = fields.Nested(WorkOrderCountsSchema)
    upcoming = fields.List(fields.Nested(WorkOrderSchema))
