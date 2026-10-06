"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useLogout } from "@/features/auth/hooks";
import { navFor } from "@/features/navigation/nav";
import { activeMembership } from "@/features/organizations/membership";
import { OrganizationSwitcher } from "@/features/organizations/organization-switcher";
import type { CurrentUser } from "@/lib/api/auth";

export function AppShell({
  user,
  children,
}: {
  user: CurrentUser;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const logout = useLogout();
  const items = navFor(activeMembership(user)?.role ?? null);

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link
            href="/dashboard"
            className="text-lg font-bold tracking-tight text-indigo-600"
          >
            PropFlow
          </Link>
          <div className="flex flex-wrap items-center gap-4">
            <OrganizationSwitcher user={user} />
            <span className="hidden text-sm text-slate-600 md:inline">
              {user.full_name}
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
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 md:flex-row">
        <nav aria-label="Main" className="md:w-48 md:shrink-0">
          <ul className="flex gap-1 overflow-x-auto md:flex-col">
            {items.map((item) => {
              const current =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={current ? "page" : undefined}
                    className={`block whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium ${
                      current
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
