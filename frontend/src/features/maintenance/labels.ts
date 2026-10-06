import {
  CATEGORIES,
  PRIORITIES,
  type Category,
  type MaintenanceRequest,
  type MaintenanceStatus,
  type Priority,
} from "@/lib/api/maintenance";

export const CATEGORY_LABELS: Record<Category, string> = {
  plumbing: "Plumbing",
  electrical: "Electrical",
  water: "Water supply",
  heating_cooling: "Heating and cooling",
  appliance: "Appliance",
  security: "Security",
  structural: "Structural",
  cleaning: "Cleaning",
  other: "Other",
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
};

export const STATUS_LABELS: Record<MaintenanceStatus, string> = {
  submitted: "Submitted",
  triaged: "Triaged",
  assigned: "Assigned",
  in_progress: "In progress",
  waiting: "Waiting",
  resolved: "Resolved",
  closed: "Closed",
};

export const STATUS_STYLES: Record<MaintenanceStatus, string> = {
  submitted: "bg-sky-50 text-sky-700 ring-sky-200",
  triaged: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  assigned: "bg-violet-50 text-violet-700 ring-violet-200",
  in_progress: "bg-amber-50 text-amber-800 ring-amber-200",
  waiting: "bg-orange-50 text-orange-800 ring-orange-200",
  resolved: "bg-green-50 text-green-700 ring-green-200",
  closed: "bg-slate-100 text-slate-600 ring-slate-200",
};

export const CATEGORY_OPTIONS = CATEGORIES.map((value) => ({
  value,
  label: CATEGORY_LABELS[value],
}));
export const PRIORITY_OPTIONS = PRIORITIES.map((value) => ({
  value,
  label: PRIORITY_LABELS[value],
}));

export function locationOf(request: MaintenanceRequest): string {
  return `${request.property.name} · ${request.unit ? `Unit ${request.unit.label}` : "Common area"}`;
}
