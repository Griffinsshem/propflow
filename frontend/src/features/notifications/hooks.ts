"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { notificationsApi } from "@/lib/api/notifications";

export const notificationKeys = {
  all: (orgId: string) => ["org", orgId, "notifications"] as const,
  unread: (orgId: string) => ["org", orgId, "notifications", "unread-count"] as const,
  list: (orgId: string, unreadOnly: boolean) =>
    ["org", orgId, "notifications", "list", unreadOnly ? "unread" : "all"] as const,
};

export function useUnreadCount(orgId: string) {
  return useQuery({
    queryKey: notificationKeys.unread(orgId),
    queryFn: ({ signal }) => notificationsApi.unreadCount(signal),
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

export function useNotifications(orgId: string, unreadOnly: boolean) {
  return useInfiniteQuery({
    queryKey: notificationKeys.list(orgId, unreadOnly),
    queryFn: ({ pageParam, signal }) =>
      notificationsApi.list({ unreadOnly, cursor: pageParam ?? undefined }, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    staleTime: 0,
    refetchOnMount: "always",
  });
}

function useNotificationChange<T>(orgId: string, mutationFn: (input: T) => Promise<unknown>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: notificationKeys.all(orgId) }),
  });
}

export const useMarkRead = (orgId: string) =>
  useNotificationChange(orgId, (id: string) => notificationsApi.markRead(id));
export const useMarkAllRead = (orgId: string) =>
  useNotificationChange(orgId, () => notificationsApi.markAllRead());
