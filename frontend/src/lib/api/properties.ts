import { apiRequest } from "./client";
import type { Page } from "./pagination";

export const PROPERTY_TYPES = [
  "residential",
  "commercial",
  "mixed_use",
  "estate",
] as const;
export const PROPERTY_STATUSES = ["active", "archived"] as const;
export const UNIT_STATUSES = ["vacant", "occupied", "unavailable"] as const;

export type PropertyType = (typeof PROPERTY_TYPES)[number];
export type PropertyStatus = (typeof PROPERTY_STATUSES)[number];
export type UnitStatus = (typeof UNIT_STATUSES)[number];

export type Property = {
  id: string;
  name: string;
  property_type: PropertyType;
  status: PropertyStatus;
  address_line: string;
  city: string;
  region: string | null;
  country_code: string;
  description: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type PropertyInput = {
  name: string;
  property_type: PropertyType;
  address_line: string;
  city: string;
  region: string | null;
  country_code: string;
  description: string | null;
};

export type PropertyChanges = Partial<
  PropertyInput & { status: PropertyStatus }
>;

export type Building = {
  id: string;
  property_id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export type Unit = {
  id: string;
  property_id: string;
  building_id: string | null;
  label: string;
  floor: number | null;
  bedrooms: number | null;
  status: UnitStatus;
  version: number;
  created_at: string;
  updated_at: string;
};

export type UnitInput = {
  building_id: string | null;
  label: string;
  floor: number | null;
  bedrooms: number | null;
  status: UnitStatus;
};

export type PropertyManager = {
  membership_id: string;
  user_id: string;
  full_name: string;
  email: string;
  assigned_at: string;
};

const enc = encodeURIComponent;
const propertyPath = (id: string) => `/properties/${enc(id)}`;

export const propertiesApi = {
  list: (status: PropertyStatus, signal?: AbortSignal) =>
    apiRequest<Page<Property>>(`/properties?status=${status}&limit=100`, {
      signal,
    }),
  get: (id: string, signal?: AbortSignal) =>
    apiRequest<Property>(propertyPath(id), { signal }),
  create: (body: PropertyInput) =>
    apiRequest<Property>("/properties", { method: "POST", body }),
  update: ({
    id,
    version,
    changes,
  }: {
    id: string;
    version: number;
    changes: PropertyChanges;
  }) =>
    apiRequest<Property>(propertyPath(id), {
      method: "PATCH",
      body: { ...changes, version },
    }),
  listBuildings: (id: string, signal?: AbortSignal) =>
    apiRequest<Building[]>(`${propertyPath(id)}/buildings`, { signal }),
  createBuilding: ({
    propertyId,
    name,
  }: {
    propertyId: string;
    name: string;
  }) =>
    apiRequest<Building>(`${propertyPath(propertyId)}/buildings`, {
      method: "POST",
      body: { name },
    }),
  listManagers: (id: string, signal?: AbortSignal) =>
    apiRequest<PropertyManager[]>(`${propertyPath(id)}/managers`, { signal }),
  assignManager: ({
    propertyId,
    membershipId,
  }: {
    propertyId: string;
    membershipId: string;
  }) =>
    apiRequest<PropertyManager>(`${propertyPath(propertyId)}/managers`, {
      method: "POST",
      body: { membership_id: membershipId },
    }),
  unassignManager: ({
    propertyId,
    membershipId,
  }: {
    propertyId: string;
    membershipId: string;
  }) =>
    apiRequest<void>(
      `${propertyPath(propertyId)}/managers/${enc(membershipId)}`,
      {
        method: "DELETE",
      },
    ),
};

export const unitsApi = {
  listForProperty: (propertyId: string, signal?: AbortSignal) =>
    apiRequest<Page<Unit>>(`/units?property_id=${enc(propertyId)}&limit=100`, {
      signal,
    }),
  get: (id: string, signal?: AbortSignal) =>
    apiRequest<Unit>(`/units/${enc(id)}`, { signal }),
  create: (body: UnitInput & { property_id: string }) =>
    apiRequest<Unit>("/units", { method: "POST", body }),
  update: ({
    id,
    version,
    changes,
  }: {
    id: string;
    version: number;
    changes: Partial<UnitInput>;
  }) =>
    apiRequest<Unit>(`/units/${enc(id)}`, {
      method: "PATCH",
      body: { ...changes, version },
    }),
};
