"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/errors";
import { maintenanceApi, type MaintenanceFilters } from "@/lib/api/maintenance";

const NONE = "none";

export const maintenanceKeys = {
  all: (orgId: string) => ["org", orgId, "maintenance"] as const,
  list: (orgId: string, filters: MaintenanceFilters) =>
    [
      "org",
      orgId,
      "maintenance",
      "list",
      filters.status ?? "",
      filters.priority ?? "",
      filters.propertyId ?? "",
    ] as const,
  detail: (orgId: string, id: string) => ["org", orgId, "maintenance", "detail", id] as const,
};

export function useMaintenanceList(orgId: string | null, filters: MaintenanceFilters) {
  return useQuery({
    queryKey: maintenanceKeys.list(orgId ?? NONE, filters),
    queryFn: ({ signal }) => maintenanceApi.list(filters, signal),
    enabled: orgId !== null,
  });
}

export function useMaintenanceRequest(orgId: string | null, id: string) {
  return useQuery({
    queryKey: maintenanceKeys.detail(orgId ?? NONE, id),
    queryFn: ({ signal }) => maintenanceApi.get(id, signal),
    enabled: orgId !== null,
    retry: (failures, error) =>
      !(error instanceof ApiError && error.status === 404) && failures < 2,
  });
}

export function useCreateMaintenanceRequest(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: maintenanceApi.create,
    onSuccess: async (request) => {
      queryClient.setQueryData(maintenanceKeys.detail(orgId, request.id), request);
      await queryClient.invalidateQueries({
        queryKey: [...maintenanceKeys.all(orgId), "list"],
      });
    },
  });
}
