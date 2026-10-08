"use client";

import { Bell } from "lucide-react";
import Link from "next/link";

import { useUnreadCount } from "@/features/notifications/hooks";

export function NotificationBell({ orgId }: { orgId: string }) {
  const unread = useUnreadCount(orgId).data?.unread ?? 0;
  return (
    <Link
      href="/notifications"
      aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
      className="relative inline-flex h-11 w-11 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 hover:text-slate-900"
    >
      <Bell aria-hidden className="h-5 w-5" />
      {unread > 0 ? (
        <span
          aria-hidden
          className="absolute right-1 top-1 min-w-5 rounded-full bg-red-600 px-1 text-center text-xs font-semibold leading-5 text-white"
        >
          {unread > 99 ? "99+" : unread}
        </span>
      ) : null}
    </Link>
  );
}
