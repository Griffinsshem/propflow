import type { WorkOrder, WorkOrderStatus } from "@/lib/api/work-orders";

export const WORK_ORDER_STATUS_LABELS: Record<WorkOrderStatus, string> = {
  assigned: "Assigned",
  accepted: "Accepted",
  declined: "Declined",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
};

export const WORK_ORDER_STATUS_STYLES: Record<WorkOrderStatus, string> = {
  assigned: "bg-violet-50 text-violet-700 ring-violet-200",
  accepted: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  declined: "bg-orange-50 text-orange-800 ring-orange-200",
  in_progress: "bg-amber-50 text-amber-800 ring-amber-200",
  completed: "bg-green-50 text-green-700 ring-green-200",
  cancelled: "bg-slate-100 text-slate-600 ring-slate-200",
};

export function locationLabel(order: WorkOrder): string {
  const unit = order.location.unit_label ? `Unit ${order.location.unit_label}` : "Common area";
  return `${order.location.property_name} · ${unit}`;
}
