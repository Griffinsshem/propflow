"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { maintenanceKeys } from "@/features/maintenance/hooks";
import { ApiError } from "@/lib/api/errors";
import { workOrdersApi, type WorkOrderFilters } from "@/lib/api/work-orders";

const NONE = "none";

export const workOrderKeys = {
  all: (orgId: string) => ["org", orgId, "work-orders"] as const,
  list: (orgId: string, filters: WorkOrderFilters) =>
    [
      "org",
      orgId,
      "work-orders",
      "list",
      filters.status ?? "",
      filters.contractorId ?? "",
      filters.requestId ?? "",
      filters.overdue ? "overdue" : "",
    ] as const,
  detail: (orgId: string, id: string) => ["org", orgId, "work-orders", "detail", id] as const,
  history: (orgId: string, id: string) =>
    ["org", orgId, "work-orders", "detail", id, "history"] as const,
};

export function useWorkOrders(orgId: string | null, filters: WorkOrderFilters) {
  return useQuery({
    queryKey: workOrderKeys.list(orgId ?? NONE, filters),
    queryFn: ({ signal }) => workOrdersApi.list(filters, signal),
    enabled: orgId !== null,
  });
}

export function useWorkOrder(orgId: string | null, id: string) {
  return useQuery({
    queryKey: workOrderKeys.detail(orgId ?? NONE, id),
    queryFn: ({ signal }) => workOrdersApi.get(id, signal),
    enabled: orgId !== null,
    retry: (failures, error) =>
      !(error instanceof ApiError && error.status === 404) && failures < 2,
  });
}

export function useWorkOrderHistory(orgId: string, id: string) {
  return useQuery({
    queryKey: workOrderKeys.history(orgId, id),
    queryFn: ({ signal }) => workOrdersApi.history(id, signal),
  });
}

/** Work orders and their requests move together: refresh both after any change. */
async function refreshBoth(queryClient: ReturnType<typeof useQueryClient>, orgId: string) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: workOrderKeys.all(orgId) }),
    queryClient.invalidateQueries({ queryKey: maintenanceKeys.all(orgId) }),
  ]);
}

export function useCreateWorkOrder(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: workOrdersApi.create,
    onSettled: () => refreshBoth(queryClient, orgId),
  });
}

export function useChangeWorkOrderStatus(orgId: string, id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (change: {
      status: Parameters<typeof workOrdersApi.changeStatus>[0]["status"];
      reason: string | null;
      version: number;
    }) => workOrdersApi.changeStatus({ id, ...change }),
    onSuccess: (order) => queryClient.setQueryData(workOrderKeys.detail(orgId, id), order),
    onSettled: () => refreshBoth(queryClient, orgId),
  });
}
