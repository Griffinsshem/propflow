import { apiRequest } from "./client";
import type { Page } from "./pagination";

export const CATEGORIES = [
  "plumbing",
  "electrical",
  "water",
  "heating_cooling",
  "appliance",
  "security",
  "structural",
  "cleaning",
  "other",
] as const;
export const PRIORITIES = ["low", "normal", "high", "urgent"] as const;
export const STATUSES = [
  "submitted",
  "triaged",
  "assigned",
  "in_progress",
  "waiting",
  "resolved",
  "closed",
] as const;

export type Category = (typeof CATEGORIES)[number];
export type Priority = (typeof PRIORITIES)[number];
export type MaintenanceStatus = (typeof STATUSES)[number];

export type MaintenanceRequest = {
  id: string;
  title: string;
  description: string;
  category: Category;
  priority: Priority;
  status: MaintenanceStatus;
  access_notes: string | null;
  property: { id: string; name: string };
  unit: { id: string; label: string } | null;
  reported_by: { membership_id: string; full_name: string };
  version: number;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
  /** Present on single-request reads: the moves this user may make right now. */
  allowed_transitions?: MaintenanceStatus[];
};

/** Tenants send no location (the API uses their tenant profile); staff send a property. */
export type MaintenanceInput = {
  category: Category;
  priority: Priority;
  title: string;
  description: string;
  access_notes: string | null;
  property_id?: string;
  unit_id?: string;
};

export type MaintenanceFilters = {
  status?: MaintenanceStatus;
  priority?: Priority;
  propertyId?: string;
};

function listQuery(filters: MaintenanceFilters): string {
  const params = new URLSearchParams({ limit: "50" });
  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.propertyId) params.set("property_id", filters.propertyId);
  return params.toString();
}

export const maintenanceApi = {
  list: (filters: MaintenanceFilters, signal?: AbortSignal) =>
    apiRequest<Page<MaintenanceRequest>>(`/maintenance?${listQuery(filters)}`, { signal }),
  get: (id: string, signal?: AbortSignal) =>
    apiRequest<MaintenanceRequest>(`/maintenance/${encodeURIComponent(id)}`, { signal }),
  create: (body: MaintenanceInput) =>
    apiRequest<MaintenanceRequest>("/maintenance", { method: "POST", body }),
};
