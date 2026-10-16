import type { CurrentUser, Role } from "./auth";
import { apiRequest } from "./client";

/** Private demo sandboxes (ADR 0021). Both answer like a sign-in and set its cookies. */
export const demoApi = {
  start: () => apiRequest<CurrentUser>("/demo", { method: "POST" }),
  viewAs: (role: Role) =>
    apiRequest<CurrentUser>("/demo/view-as", { method: "POST", body: { role } }),
};
