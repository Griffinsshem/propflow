import { apiRequest } from "./client";
import type { Specialty } from "./contractors";
import type { Category, MaintenanceStatus, PersonRef, Priority } from "./maintenance";
import type { Page } from "./pagination";

export const WORK_ORDER_STATUSES = [
  "assigned",
  "accepted",
  "declined",
  "in_progress",
  "completed",
  "cancelled",
] as const;
export type WorkOrderStatus = (typeof WORK_ORDER_STATUSES)[number];
export const ACTIVE_WORK_ORDER_STATUSES: readonly WorkOrderStatus[] = [
  "assigned",
  "accepted",
  "in_progress",
];

export type WorkOrder = {
  id: string;
  status: WorkOrderStatus;
  priority: Priority;
  description: string | null;
  due_date: string | null;
  is_overdue: boolean;
  completed_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  contractor: { id: string; business_name: string; specialty: Specialty };
  request: {
    id: string;
    title: string;
    description: string;
    category: Category;
    status: MaintenanceStatus;
    access_notes: string | null;
  };
  location: {
    property_id: string;
    property_name: string;
    address_line: string;
    city: string;
    unit_id: string | null;
    unit_label: string | null;
  };
  allowed_transitions?: WorkOrderStatus[];
};

export type WorkOrderInput = {
  request_id: string;
  contractor_id: string;
  priority: Priority;
  description: string | null;
  due_date: string | null;
};

export type WorkOrderFilters = {
  status?: WorkOrderStatus;
  contractorId?: string;
  requestId?: string;
  overdue?: boolean;
};

export type WorkOrderHistoryEntry = {
  from_status: WorkOrderStatus | null;
  to_status: WorkOrderStatus;
  reason: string | null;
  changed_by: PersonRef;
  created_at: string;
};

const enc = encodeURIComponent;
const path = (id: string) => `/work-orders/${enc(id)}`;

function listQuery(filters: WorkOrderFilters): string {
  const params = new URLSearchParams({ limit: "50" });
  if (filters.status) params.set("status", filters.status);
  if (filters.contractorId) params.set("contractor_id", filters.contractorId);
  if (filters.requestId) params.set("request_id", filters.requestId);
  if (filters.overdue) params.set("overdue", "true");
  return params.toString();
}

export const workOrdersApi = {
  list: (filters: WorkOrderFilters, signal?: AbortSignal) =>
    apiRequest<Page<WorkOrder>>(`/work-orders?${listQuery(filters)}`, { signal }),
  get: (id: string, signal?: AbortSignal) => apiRequest<WorkOrder>(path(id), { signal }),
  history: (id: string, signal?: AbortSignal) =>
    apiRequest<WorkOrderHistoryEntry[]>(`${path(id)}/history`, { signal }),
  create: (body: WorkOrderInput) => apiRequest<WorkOrder>("/work-orders", { method: "POST", body }),
  changeStatus: ({
    id,
    ...body
  }: {
    id: string;
    status: WorkOrderStatus;
    reason: string | null;
    version: number;
  }) => apiRequest<WorkOrder>(`${path(id)}/status`, { method: "POST", body }),
};
