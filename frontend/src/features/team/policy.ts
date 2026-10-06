import type { Role } from "@/lib/api/auth";

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Owner",
  manager: "Manager",
  tenant: "Tenant",
  contractor: "Contractor",
};

// Mirrors the API's can_invite policy so the form only offers allowed roles.
const INVITABLE: Record<Role, readonly Role[]> = {
  owner: ["manager", "contractor", "tenant", "owner"],
  manager: ["contractor", "tenant"],
  tenant: [],
  contractor: [],
};

export function invitableRoles(role: Role): readonly Role[] {
  return INVITABLE[role];
}
