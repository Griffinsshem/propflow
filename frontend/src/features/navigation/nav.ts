import {
  Building2,
  ClipboardList,
  HardHat,
  LayoutDashboard,
  Settings,
  Users,
  UsersRound,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import type { Role } from "@/lib/api/auth";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  roles: readonly Role[];
};

const EVERYONE: readonly Role[] = ["owner", "manager", "tenant", "contractor"];

/**
 * Sections appear here as their pages ship. Roles mirror the API's permission matrix for
 * convenience only: the API authorizes every request regardless of what is shown.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard", roles: EVERYONE },
  {
    href: "/maintenance",
    icon: Wrench,
    label: "Maintenance",
    roles: ["owner", "manager", "tenant"],
  },
  {
    href: "/work-orders",
    icon: ClipboardList,
    label: "Work orders",
    roles: ["owner", "manager", "contractor"],
  },
  { href: "/properties", icon: Building2, label: "Properties", roles: ["owner", "manager"] },
  { href: "/tenants", icon: Users, label: "Tenants", roles: ["owner", "manager"] },
  { href: "/contractors", icon: HardHat, label: "Contractors", roles: ["owner", "manager"] },
  { href: "/settings/team", icon: UsersRound, label: "Team", roles: ["owner", "manager"] },
  {
    href: "/settings/organization",
    icon: Settings,
    label: "Organization",
    roles: ["owner", "manager"],
  },
];

export function navFor(role: Role | null): NavItem[] {
  if (role === null) return NAV_ITEMS.filter((item) => item.href === "/dashboard");
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}
