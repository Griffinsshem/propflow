import type { Role } from "@/lib/api/auth";

export type NavItem = { href: string; label: string; roles: readonly Role[] };

const EVERYONE: readonly Role[] = ["owner", "manager", "tenant", "contractor"];

/**
 * Sections appear here as their pages ship. Roles mirror the API's permission matrix for
 * convenience only: the API authorizes every request regardless of what is shown.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/dashboard", label: "Dashboard", roles: EVERYONE },
  { href: "/maintenance", label: "Maintenance", roles: ["owner", "manager", "tenant"] },
  { href: "/properties", label: "Properties", roles: ["owner", "manager"] },
  { href: "/tenants", label: "Tenants", roles: ["owner", "manager"] },
  { href: "/contractors", label: "Contractors", roles: ["owner", "manager"] },
  { href: "/settings/team", label: "Team", roles: ["owner", "manager"] },
  {
    href: "/settings/organization",
    label: "Organization",
    roles: ["owner", "manager"],
  },
];

export function navFor(role: Role | null): NavItem[] {
  if (role === null) return NAV_ITEMS.filter((item) => item.href === "/dashboard");
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}
