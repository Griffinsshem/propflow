import type { CurrentUser, Membership } from "@/lib/api/auth";

/** The membership for the organization this session is working in, if any. */
export function activeMembership(user: CurrentUser): Membership | null {
  return user.memberships.find((m) => m.organization_id === user.active_organization_id) ?? null;
}
