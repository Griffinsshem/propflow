"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { invitationsKey } from "@/features/team/hooks";
import { tenantsApi, type TenantFilters } from "@/lib/api/tenants";

const NONE = "none";

export const tenantKeys = {
  all: (orgId: string) => ["org", orgId, "tenants"] as const,
  list: (orgId: string, filters: TenantFilters) =>
    ["org", orgId, "tenants", filters.propertyId ?? "", filters.unitId ?? ""] as const,
  mine: (orgId: string) => ["org", orgId, "my-tenancy"] as const,
};

export function useTenants(orgId: string | null, filters: TenantFilters) {
  return useQuery({
    queryKey: tenantKeys.list(orgId ?? NONE, filters),
    queryFn: ({ signal }) => tenantsApi.list(filters, signal),
    enabled: orgId !== null,
  });
}

export function useMyTenancy(orgId: string) {
  return useQuery({
    queryKey: tenantKeys.mine(orgId),
    queryFn: ({ signal }) => tenantsApi.me(signal),
  });
}

export function useInviteTenant(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: tenantsApi.invite,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: invitationsKey(orgId) }),
  });
}

/** Tenancy changes also change unit occupancy, so refresh tenants, properties and units. */
function useTenancyChange<T>(orgId: string, mutationFn: (input: T) => Promise<unknown>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: tenantKeys.all(orgId) }),
        queryClient.invalidateQueries({ queryKey: ["org", orgId, "property"] }),
        queryClient.invalidateQueries({ queryKey: ["org", orgId, "unit"] }),
      ]);
    },
  });
}

export const useMoveTenant = (orgId: string) => useTenancyChange(orgId, tenantsApi.update);
export const useEndTenancy = (orgId: string) => useTenancyChange(orgId, tenantsApi.deactivate);
