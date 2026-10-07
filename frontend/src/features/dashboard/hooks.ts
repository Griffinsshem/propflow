"use client";

import { useQuery } from "@tanstack/react-query";

import { dashboardsApi } from "@/lib/api/dashboards";

const key = (orgId: string, kind: string, extra = "") =>
  ["org", orgId, "dashboard", kind, extra] as const;
// Dashboards summarize what just happened elsewhere: always refetch when opened.
const fresh = { staleTime: 0, refetchOnMount: "always" as const };

export function useOrganizationDashboard(orgId: string) {
  return useQuery({
    queryKey: key(orgId, "organization"),
    queryFn: ({ signal }) => dashboardsApi.organization(signal),
    ...fresh,
  });
}

export function useOperationsDashboard(orgId: string, propertyId: string | null) {
  return useQuery({
    queryKey: key(orgId, "operations", propertyId ?? ""),
    queryFn: ({ signal }) => dashboardsApi.operations(propertyId, signal),
    ...fresh,
  });
}

export function useTenantDashboard(orgId: string) {
  return useQuery({
    queryKey: key(orgId, "tenant"),
    queryFn: ({ signal }) => dashboardsApi.tenant(signal),
    ...fresh,
  });
}

export function useContractorDashboard(orgId: string) {
  return useQuery({
    queryKey: key(orgId, "contractor"),
    queryFn: ({ signal }) => dashboardsApi.contractor(signal),
    ...fresh,
  });
}
