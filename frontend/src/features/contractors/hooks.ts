"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { invitationsKey } from "@/features/team/hooks";
import { contractorsApi, type ContractorFilters } from "@/lib/api/contractors";
import { ApiError } from "@/lib/api/errors";

const NONE = "none";

export const contractorKeys = {
  all: (orgId: string) => ["org", orgId, "contractors"] as const,
  list: (orgId: string, filters: ContractorFilters) =>
    ["org", orgId, "contractors", "list", filters.status ?? "", filters.specialty ?? ""] as const,
  detail: (orgId: string, id: string) => ["org", orgId, "contractors", "detail", id] as const,
};

export function useContractors(orgId: string | null, filters: ContractorFilters) {
  return useQuery({
    queryKey: contractorKeys.list(orgId ?? NONE, filters),
    queryFn: ({ signal }) => contractorsApi.list(filters, signal),
    enabled: orgId !== null,
  });
}

export function useContractor(orgId: string | null, id: string) {
  return useQuery({
    queryKey: contractorKeys.detail(orgId ?? NONE, id),
    queryFn: ({ signal }) => contractorsApi.get(id, signal),
    enabled: orgId !== null,
    retry: (failures, error) =>
      !(error instanceof ApiError && error.status === 404) && failures < 2,
  });
}

export function useCreateContractor(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractorsApi.create,
    onSuccess: async (contractor) => {
      queryClient.setQueryData(contractorKeys.detail(orgId, contractor.id), contractor);
      await queryClient.invalidateQueries({ queryKey: [...contractorKeys.all(orgId), "list"] });
    },
  });
}

export function useUpdateContractor(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractorsApi.update,
    onSuccess: async (contractor) => {
      queryClient.setQueryData(contractorKeys.detail(orgId, contractor.id), contractor);
      await queryClient.invalidateQueries({ queryKey: [...contractorKeys.all(orgId), "list"] });
    },
  });
}

export function useInviteContractorLogin(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contractorsApi.inviteLogin,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: invitationsKey(orgId) }),
  });
}
