import { apiRequest } from "./client";
import type { MaintenanceRequest } from "./maintenance";
import type { WorkOrder } from "./work-orders";

export type RequestCounts = {
  open: number;
  new: number;
  urgent: number;
  in_flight: number;
  in_progress: number;
  waiting: number;
  resolved: number;
  closed: number;
  resolved_this_month: number;
};

export type WorkOrderCounts = {
  awaiting_acceptance: number;
  accepted: number;
  in_progress: number;
  active: number;
  overdue: number;
  completed_this_month: number;
};

export type OrganizationDashboard = {
  counts: {
    properties: number;
    units: number;
    active_tenants: number;
    open_requests: number;
    active_work_orders: number;
  };
};

export type OperationsDashboard = {
  requests: RequestCounts;
  work_orders: WorkOrderCounts;
  recent_requests: MaintenanceRequest[];
  recently_updated: MaintenanceRequest[];
  overdue_work_orders: WorkOrder[];
};

export type TenantDashboard = {
  requests: {
    submitted: number;
    in_progress: number;
    waiting: number;
    resolved: number;
    closed: number;
  };
  recent_requests: MaintenanceRequest[];
};

export type ContractorDashboard = { work_orders: WorkOrderCounts; upcoming: WorkOrder[] };

export const dashboardsApi = {
  organization: (signal?: AbortSignal) =>
    apiRequest<OrganizationDashboard>("/dashboard/organization", { signal }),
  operations: (propertyId: string | null, signal?: AbortSignal) =>
    apiRequest<OperationsDashboard>(
      `/dashboard/operations${propertyId ? `?property_id=${encodeURIComponent(propertyId)}` : ""}`,
      { signal },
    ),
  tenant: (signal?: AbortSignal) => apiRequest<TenantDashboard>("/dashboard/tenant", { signal }),
  contractor: (signal?: AbortSignal) =>
    apiRequest<ContractorDashboard>("/dashboard/contractor", { signal }),
};
