"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { CURRENT_USER_KEY } from "@/features/auth/hooks";
import { organizationsApi } from "@/lib/api/organizations";

// Convention: organization-scoped data lives under ["org", organizationId, ...].
export const organizationKey = (id: string) => ["org", id, "details"] as const;

export function useOrganization(id: string | null) {
  return useQuery({
    queryKey: organizationKey(id ?? "none"),
    queryFn: ({ signal }) => organizationsApi.get(id ?? "", signal),
    enabled: id !== null,
  });
}

export function useCreateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: organizationsApi.create,
    // The API also switches the session to the new organization.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CURRENT_USER_KEY }),
  });
}

export function useActivateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: organizationsApi.activate,
    onSuccess: async () => {
      // Everything cached belongs to the previous organization: drop it before refetching.
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== "auth",
      });
      await queryClient.invalidateQueries({ queryKey: CURRENT_USER_KEY });
    },
  });
}

export function useRenameOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: organizationsApi.rename,
    onSuccess: async (organization) => {
      queryClient.setQueryData(organizationKey(organization.id), organization);
      await queryClient.invalidateQueries({ queryKey: CURRENT_USER_KEY });
    },
  });
}
