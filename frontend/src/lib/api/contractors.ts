import { apiRequest } from "./client";
import type { Invitation } from "./invitations";
import type { Page } from "./pagination";

export const SPECIALTIES = [
  "general",
  "plumbing",
  "electrical",
  "carpentry",
  "cleaning",
  "security",
  "hvac",
  "painting",
] as const;
export const CONTRACTOR_STATUSES = ["active", "inactive"] as const;

export type Specialty = (typeof SPECIALTIES)[number];
export type ContractorStatus = (typeof CONTRACTOR_STATUSES)[number];

export type Contractor = {
  id: string;
  business_name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  specialty: Specialty;
  status: ContractorStatus;
  has_login: boolean;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ContractorInput = {
  business_name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  specialty: Specialty;
};

export type ContractorChanges = Partial<ContractorInput & { status: ContractorStatus }>;
export type ContractorFilters = { status?: ContractorStatus; specialty?: Specialty };

const enc = encodeURIComponent;
const path = (id: string) => `/contractors/${enc(id)}`;

function listQuery(filters: ContractorFilters): string {
  const params = new URLSearchParams({ limit: "100" });
  if (filters.status) params.set("status", filters.status);
  if (filters.specialty) params.set("specialty", filters.specialty);
  return params.toString();
}

export const contractorsApi = {
  list: (filters: ContractorFilters, signal?: AbortSignal) =>
    apiRequest<Page<Contractor>>(`/contractors?${listQuery(filters)}`, { signal }),
  get: (id: string, signal?: AbortSignal) => apiRequest<Contractor>(path(id), { signal }),
  create: (body: ContractorInput) =>
    apiRequest<Contractor>("/contractors", { method: "POST", body }),
  update: ({ id, version, changes }: { id: string; version: number; changes: ContractorChanges }) =>
    apiRequest<Contractor>(path(id), { method: "PATCH", body: { ...changes, version } }),
  inviteLogin: ({ id, email }: { id: string; email: string }) =>
    apiRequest<Invitation>(`${path(id)}/invite`, { method: "POST", body: { email } }),
};
