import { apiRequest } from "./client";
import type { Invitation } from "./invitations";
import type { Page } from "./pagination";

export type TenantUnit = {
  id: string;
  label: string;
  building_id: string | null;
  property_id: string;
  property_name: string | null;
};

export type Tenant = {
  id: string;
  membership_id: string;
  user_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  status: string;
  move_in_date: string | null;
  version: number;
  unit: TenantUnit | null;
};

export type TenantFilters = { propertyId?: string; unitId?: string };

export type TenantChanges = {
  unit_id?: string | null;
  phone?: string | null;
  move_in_date?: string | null;
};

function listQuery(filters: TenantFilters): string {
  const params = new URLSearchParams({ limit: "100" });
  if (filters.propertyId) params.set("property_id", filters.propertyId);
  if (filters.unitId) params.set("unit_id", filters.unitId);
  return params.toString();
}

const enc = encodeURIComponent;

export const tenantsApi = {
  list: (filters: TenantFilters, signal?: AbortSignal) =>
    apiRequest<Page<Tenant>>(`/tenants?${listQuery(filters)}`, { signal }),
  me: (signal?: AbortSignal) => apiRequest<Tenant>("/tenants/me", { signal }),
  invite: ({ email, unitId }: { email: string; unitId: string }) =>
    apiRequest<Invitation>("/tenants", { method: "POST", body: { email, unit_id: unitId } }),
  update: ({ id, version, changes }: { id: string; version: number; changes: TenantChanges }) =>
    apiRequest<Tenant>(`/tenants/${enc(id)}`, { method: "PATCH", body: { ...changes, version } }),
  deactivate: (id: string) =>
    apiRequest<void>(`/tenants/${enc(id)}/deactivate`, { method: "POST" }),
};
