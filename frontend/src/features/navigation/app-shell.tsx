"use client";

import { LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useLogout } from "@/features/auth/hooks";
import { navFor, type NavItem } from "@/features/navigation/nav";
import { NotificationBell } from "@/features/notifications/notification-bell";
import { activeMembership } from "@/features/organizations/membership";
import { OrganizationSwitcher } from "@/features/organizations/organization-switcher";
import type { CurrentUser } from "@/lib/api/auth";

function NavLinks({
  items,
  pathname,
  onNavigate,
  className = "",
}: {
  items: NavItem[];
  pathname: string;
  onNavigate?: () => void;
  className?: string;
}) {
  return (
    <nav aria-label="Main" className={className}>
      <ul className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const current = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={current ? "page" : undefined}
                onClick={onNavigate}
                className={`flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium ${
                  current ? "bg-indigo-50 text-indigo-700" : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <Icon aria-hidden className="h-4 w-4 shrink-0" />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

const FOCUSABLE = "a[href], button:not([disabled]), select:not([disabled]), input:not([disabled])";

/** The phone menu: a dialog that traps focus, closes on Escape or outside tap, locks scrolling. */
function MobileMenu({
  user,
  items,
  pathname,
  onClose,
}: {
  user: CurrentUser;
  items: NavItem[];
  pathname: string;
  onClose: () => void;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const logout = useLogout();

  useEffect(() => {
    closeButton.current?.focus();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = panel.current?.querySelectorAll<HTMLElement>(FOCUSABLE);
    const first = focusable?.[0];
    const last = focusable?.[focusable.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="fixed inset-0 z-40 md:hidden">
      <div aria-hidden className="absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div
        ref={panel}
        id="mobile-menu"
        role="dialog"
        aria-modal="true"
        aria-label="Menu"
        onKeyDown={onKeyDown}
        className="absolute inset-y-0 right-0 flex w-72 max-w-[85%] flex-col gap-5 overflow-y-auto bg-white p-4 shadow-xl"
      >
        <div className="flex items-center justify-between">
          <span className="font-semibold text-slate-900">Menu</span>
          <button
            ref={closeButton}
            type="button"
            aria-label="Close menu"
            onClick={onClose}
            className="inline-flex h-11 w-11 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100"
          >
            <X aria-hidden className="h-5 w-5" />
          </button>
        </div>
        <OrganizationSwitcher user={user} />
        <NavLinks items={items} pathname={pathname} onNavigate={onClose} />
        <div className="mt-auto space-y-3 border-t border-slate-100 pt-4">
          <div className="text-sm">
            <p className="font-medium text-slate-900">{user.full_name}</p>
            <p className="truncate text-slate-500">{user.email}</p>
          </div>
          <Button
            type="button"
            variant="secondary"
            className="w-full"
            pending={logout.isPending}
            onClick={() => logout.mutate()}
          >
            <LogOut aria-hidden className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ user, children }: { user: CurrentUser; children: ReactNode }) {
  const pathname = usePathname();
  const logout = useLogout();
  const active = activeMembership(user);
  const items = navFor(active?.role ?? null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);

  function closeMenu() {
    setMenuOpen(false);
    menuButton.current?.focus();
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4">
          <Link href="/dashboard" className="text-lg font-bold tracking-tight text-indigo-600">
            PropFlow
          </Link>
          <div className="flex items-center gap-1 md:gap-4">
            <div className="hidden md:block">
              <OrganizationSwitcher user={user} />
            </div>
            {active ? <NotificationBell orgId={active.organization_id} /> : null}
            <span className="hidden text-sm text-slate-600 lg:inline">{user.full_name}</span>
            <div className="hidden md:block">
              <Button
                type="button"
                variant="secondary"
                pending={logout.isPending}
                onClick={() => logout.mutate()}
              >
                <LogOut aria-hidden className="mr-2 h-4 w-4" />
                Sign out
              </Button>
            </div>
            <button
              ref={menuButton}
              type="button"
              aria-label="Open menu"
              aria-expanded={menuOpen}
              aria-controls="mobile-menu"
              onClick={() => setMenuOpen(true)}
              className="inline-flex h-11 w-11 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100 md:hidden"
            >
              <Menu aria-hidden className="h-6 w-6" />
            </button>
          </div>
        </div>
      </header>
      {menuOpen ? (
        <MobileMenu user={user} items={items} pathname={pathname} onClose={closeMenu} />
      ) : null}
      <div className="mx-auto flex max-w-6xl gap-6 px-4 py-4 sm:py-6">
        <NavLinks
          items={items}
          pathname={pathname}
          className="hidden md:block md:w-52 md:shrink-0"
        />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
