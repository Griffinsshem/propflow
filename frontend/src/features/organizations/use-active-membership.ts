"use client";

import { useCurrentUser } from "@/features/auth/hooks";
import { activeMembership } from "@/features/organizations/membership";
import type { Membership } from "@/lib/api/auth";

export function useActiveMembership(): Membership | null {
  const { data: user } = useCurrentUser();
  return user ? activeMembership(user) : null;
}
