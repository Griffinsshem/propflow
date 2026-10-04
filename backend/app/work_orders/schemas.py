"""Work order request/response schemas."""

from __future__ import annotations

from marshmallow import Schema, fields, validate

from app.common.pagination import PageQuerySchema
from app.common.validation import plain_text
from app.maintenance.models import MaintenancePriority
from app.maintenance.schemas import StatusHistorySchema
from app.work_orders.models import WorkOrderStatus

PRIORITIES = [p.value for p in MaintenancePriority]
STATUSES = [s.value for s in WorkOrderStatus]


class WorkOrderCreateSchema(Schema):
    request_id = fields.UUID(required=True)
    contractor_id = fields.UUID(required=True)
    priority = fields.String(load_default=None, validate=validate.OneOf(PRIORITIES))
    description = fields.String(
        load_default=None, allow_none=True, validate=[validate.Length(max=2000), plain_text]
    )
    due_date = fields.Date(load_default=None, allow_none=True)


class WorkOrderUpdateSchema(Schema):
    version = fields.Integer(required=True, validate=validate.Range(min=1))
    priority = fields.String(validate=validate.OneOf(PRIORITIES))
    description = fields.String(allow_none=True, validate=[validate.Length(max=2000), plain_text])
    due_date = fields.Date(allow_none=True)


class WorkOrderAssignSchema(Schema):
    contractor_id = fields.UUID(required=True)
    version = fields.Integer(required=True, validate=validate.Range(min=1))


class WorkOrderStatusChangeSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf(STATUSES))
    reason = fields.String(
        load_default=None, allow_none=True, validate=[validate.Length(max=1000), plain_text]
    )
    version = fields.Integer(required=True, validate=validate.Range(min=1))


class WorkOrderListQuerySchema(PageQuerySchema):
    status = fields.String(load_default=None, validate=validate.OneOf(STATUSES))
    contractor_id = fields.UUID(load_default=None)
    request_id = fields.UUID(load_default=None)
    overdue = fields.Boolean(load_default=False)


class _ContractorRefSchema(Schema):
    id = fields.UUID()
    business_name = fields.String()
    specialty = fields.String()


class _RequestRefSchema(Schema):
    id = fields.UUID()
    title = fields.String()
    description = fields.String()
    category = fields.String()
    status = fields.String()
    access_notes = fields.String(allow_none=True)


class _LocationSchema(Schema):
    property_id = fields.UUID()
    property_name = fields.String()
    address_line = fields.String()
    city = fields.String()
    unit_id = fields.UUID(allow_none=True)
    unit_label = fields.String(allow_none=True)


class WorkOrderSchema(Schema):
    id = fields.UUID()
    status = fields.String()
    priority = fields.String()
    description = fields.String(allow_none=True)
    due_date = fields.Date(allow_none=True)
    is_overdue = fields.Boolean()
    completed_at = fields.DateTime(allow_none=True)
    version = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    contractor = fields.Nested(_ContractorRefSchema)
    request = fields.Nested(_RequestRefSchema)
    location = fields.Nested(_LocationSchema)
    allowed_transitions = fields.List(fields.String())


class WorkOrderPageSchema(Schema):
    items = fields.List(fields.Nested(WorkOrderSchema))
    next_cursor = fields.String(allow_none=True)


WorkOrderHistorySchema = StatusHistorySchema
