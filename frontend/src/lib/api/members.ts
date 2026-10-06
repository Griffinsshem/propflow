import type { Role } from "./auth";
import { apiRequest } from "./client";
import type { Page } from "./pagination";

export type Member = {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  role: Role;
  status: string;
  joined_at: string;
};

const path = (id: string) => `/members/${encodeURIComponent(id)}`;

export const membersApi = {
  list: (signal?: AbortSignal) =>
    apiRequest<Page<Member>>("/members?limit=100", { signal }),
  changeRole: ({ id, role }: { id: string; role: Role }) =>
    apiRequest<Member>(path(id), { method: "PATCH", body: { role } }),
  deactivate: (id: string) =>
    apiRequest<Member>(`${path(id)}/deactivate`, { method: "POST" }),
};
