"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { maintenanceKeys } from "@/features/maintenance/hooks";
import { statusApi, type StatusChange } from "@/lib/api/maintenance";

export function useChangeStatus(orgId: string, requestId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (change: StatusChange) => statusApi.change(requestId, change),
    onSuccess: (request) =>
      queryClient.setQueryData(maintenanceKeys.detail(orgId, requestId), request),
    // Success or conflict: refresh the request, its history and every list.
    onSettled: () => queryClient.invalidateQueries({ queryKey: maintenanceKeys.all(orgId) }),
  });
}
