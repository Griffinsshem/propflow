import type { Role } from "@/lib/api/auth";

// Mirrors the API's permission matrix for the interface only; the API enforces it.
export const canReport = (role: Role) => role !== "contractor";
export const isStaff = (role: Role) => role === "owner" || role === "manager";
