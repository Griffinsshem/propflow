import { apiRequest } from "./client";
import type { Page } from "./pagination";

export type Notification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  resource_type: string;
  resource_id: string;
  read: boolean;
  created_at: string;
};

export const notificationsApi = {
  list: (
    { unreadOnly, cursor }: { unreadOnly: boolean; cursor?: string },
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams({ limit: "20" });
    if (unreadOnly) params.set("unread_only", "true");
    if (cursor) params.set("cursor", cursor);
    return apiRequest<Page<Notification>>(`/notifications?${params.toString()}`, { signal });
  },
  unreadCount: (signal?: AbortSignal) =>
    apiRequest<{ unread: number }>("/notifications/unread-count", { signal }),
  markRead: (id: string) =>
    apiRequest<Notification>(`/notifications/${encodeURIComponent(id)}/read`, { method: "POST" }),
  markAllRead: () => apiRequest<{ updated: number }>("/notifications/read-all", { method: "POST" }),
};
