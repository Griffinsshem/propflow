"use client";

import Link from "next/link";
import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { useMarkAllRead, useMarkRead, useNotifications } from "@/features/notifications/hooks";
import { linkFor } from "@/features/notifications/links";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { messageOf } from "@/lib/api/errors";
import type { Notification } from "@/lib/api/notifications";
import { formatDateTime } from "@/lib/format";
import { useQueryFilters } from "@/lib/query-filters";

function NotificationItem({ orgId, notification }: { orgId: string; notification: Notification }) {
  const markRead = useMarkRead(orgId);
  const href = linkFor(notification.resource_type, notification.resource_id);
  const open = () => {
    if (!notification.read) markRead.mutate(notification.id);
  };
  return (
    <li className={`flex gap-3 p-4 text-sm ${notification.read ? "" : "bg-indigo-50/50"}`}>
      <span
        aria-hidden
        className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${notification.read ? "bg-transparent" : "bg-indigo-600"}`}
      />
      <div className="min-w-0 flex-1 space-y-1">
        <p className={notification.read ? "text-slate-700" : "font-semibold text-slate-900"}>
          {notification.read ? null : <span className="sr-only">Unread: </span>}
          {href ? (
            <Link href={href} onClick={open} className="hover:text-indigo-600">
              {notification.title}
            </Link>
          ) : (
            notification.title
          )}
        </p>
        <p className="whitespace-pre-wrap text-slate-600">{notification.body}</p>
        <time dateTime={notification.created_at} className="text-xs text-slate-500">
          {formatDateTime(notification.created_at)}
        </time>
      </div>
      {!href && !notification.read ? (
        <Button type="button" variant="secondary" onClick={open} pending={markRead.isPending}>
          Mark as read
        </Button>
      ) : null}
    </li>
  );
}

function NotificationList() {
  const membership = useActiveMembership();
  const orgId = membership?.organization_id ?? "none";
  const [query, setQuery] = useQueryFilters((params) => ({
    unread: params.get("unread") === "1" ? "1" : "",
  }));
  const unreadOnly = query.unread === "1";
  const notifications = useNotifications(orgId, unreadOnly);
  const markAll = useMarkAllRead(orgId);

  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  const items = notifications.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
        <Button
          type="button"
          variant="secondary"
          pending={markAll.isPending}
          onClick={() => markAll.mutate(undefined)}
        >
          Mark all as read
        </Button>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={unreadOnly}
          onChange={(event) => setQuery("unread", event.target.checked ? "1" : "")}
          className="h-4 w-4 rounded border-slate-300 text-indigo-600"
        />
        Unread only
      </label>
      {markAll.isError ? <FormAlert>{messageOf(markAll.error)}</FormAlert> : null}
      {notifications.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : notifications.isError ? (
        <FormAlert>{messageOf(notifications.error)}</FormAlert>
      ) : items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          {unreadOnly ? "You're all caught up." : "No notifications yet."}
        </p>
      ) : (
        <ul
          aria-label="Notifications"
          className="divide-y divide-slate-100 overflow-hidden rounded-lg bg-white ring-1 ring-slate-200"
        >
          {items.map((notification) => (
            <NotificationItem key={notification.id} orgId={orgId} notification={notification} />
          ))}
        </ul>
      )}
      {notifications.hasNextPage ? (
        <Button
          type="button"
          variant="secondary"
          pending={notifications.isFetchingNextPage}
          onClick={() => void notifications.fetchNextPage()}
        >
          Load more
        </Button>
      ) : null}
    </div>
  );
}

// useSearchParams needs a Suspense boundary.
export default function NotificationsPage() {
  return (
    <Suspense fallback={null}>
      <NotificationList />
    </Suspense>
  );
}
