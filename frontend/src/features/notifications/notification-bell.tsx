"use client";

import Link from "next/link";

import { useUnreadCount } from "@/features/notifications/hooks";

export function NotificationBell({ orgId }: { orgId: string }) {
  const unread = useUnreadCount(orgId).data?.unread ?? 0;
  return (
    <Link
      href="/notifications"
      aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
      className="relative inline-flex rounded-md p-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
    >
      <svg
        aria-hidden
        viewBox="0 0 24 24"
        className="h-5 w-5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5m6 0a3 3 0 1 1-6 0" />
      </svg>
      {unread > 0 ? (
        <span
          aria-hidden
          className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-600 px-1 text-center text-xs font-semibold leading-5 text-white"
        >
          {unread > 99 ? "99+" : unread}
        </span>
      ) : null}
    </Link>
  );
}
