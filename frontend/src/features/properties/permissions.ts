import type { Role } from "@/lib/api/auth";

// Mirrors the API's permission matrix for the interface only; the API enforces it.
export const canManageProperties = (role: Role) => role === "owner";
export const canManageUnits = (role: Role) => role === "owner" || role === "manager";
