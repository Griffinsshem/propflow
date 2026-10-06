import type { Role } from "./auth";
import { apiRequest } from "./client";

export type Organization = {
  id: string;
  name: string;
  status: string;
  role: Role;
  created_at: string;
};

const path = (id: string) => `/organizations/${encodeURIComponent(id)}`;

export const organizationsApi = {
  get: (id: string, signal?: AbortSignal) => apiRequest<Organization>(path(id), { signal }),
  create: (name: string) =>
    apiRequest<Organization>("/organizations", { method: "POST", body: { name } }),
  rename: ({ id, name }: { id: string; name: string }) =>
    apiRequest<Organization>(path(id), { method: "PATCH", body: { name } }),
  activate: (id: string) => apiRequest<Organization>(`${path(id)}/activate`, { method: "POST" }),
};
