"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useLogout } from "@/features/auth/hooks";
import type { CurrentUser } from "@/lib/api/auth";

export function AppHeader({ user }: { user: CurrentUser }) {
  const logout = useLogout();
  const active = user.memberships.find((m) => m.organization_id === user.active_organization_id);
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/dashboard" className="text-lg font-bold tracking-tight text-indigo-600">
          PropFlow
        </Link>
        <div className="flex items-center gap-4">
          <span className="hidden text-sm text-slate-600 sm:inline">
            {user.full_name}
            {active ? ` · ${active.organization_name}` : ""}
          </span>
          <Button
            type="button"
            variant="secondary"
            pending={logout.isPending}
            onClick={() => logout.mutate()}
          >
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
