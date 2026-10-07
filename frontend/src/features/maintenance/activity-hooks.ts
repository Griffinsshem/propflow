"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { maintenanceKeys } from "@/features/maintenance/hooks";
import { activityApi } from "@/lib/api/maintenance";

// Under the request's own key: refreshing a request after a status change refreshes these too.
export const historyKey = (orgId: string, requestId: string) =>
  [...maintenanceKeys.detail(orgId, requestId), "history"] as const;
export const commentsKey = (orgId: string, requestId: string) =>
  [...maintenanceKeys.detail(orgId, requestId), "comments"] as const;

export function useHistory(orgId: string, requestId: string) {
  return useQuery({
    queryKey: historyKey(orgId, requestId),
    queryFn: ({ signal }) => activityApi.history(requestId, signal),
  });
}

export function useComments(orgId: string, requestId: string) {
  return useQuery({
    queryKey: commentsKey(orgId, requestId),
    queryFn: ({ signal }) => activityApi.comments(requestId, signal),
  });
}

export function useAddComment(orgId: string, requestId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => activityApi.addComment({ requestId, body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: commentsKey(orgId, requestId) }),
  });
}
