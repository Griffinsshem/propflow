import { apiRequest } from "./client";

export type Role = "owner" | "manager" | "tenant" | "contractor";

export type Membership = {
  organization_id: string;
  organization_name: string;
  role: Role;
};

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string;
  email_verified: boolean;
  active_organization_id: string | null;
  memberships: Membership[];
};

export type LoginInput = { email: string; password: string };
export type RegisterInput = LoginInput & { full_name: string };

export const authApi = {
  me: (signal?: AbortSignal) => apiRequest<CurrentUser>("/auth/me", { signal }),
  login: (body: LoginInput) => apiRequest<CurrentUser>("/auth/login", { method: "POST", body }),
  register: (body: RegisterInput) =>
    apiRequest<CurrentUser>("/auth/register", { method: "POST", body }),
  logout: () => apiRequest<void>("/auth/logout", { method: "POST" }),
};
