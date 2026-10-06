"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { CURRENT_USER_KEY } from "@/features/auth/hooks";
import { invitationsApi } from "@/lib/api/invitations";
import { membersApi } from "@/lib/api/members";

export const invitationsKey = (orgId: string) =>
  ["org", orgId, "invitations"] as const;
export const membersKey = (orgId: string) => ["org", orgId, "members"] as const;

export function usePendingInvitations(orgId: string) {
  return useQuery({
    queryKey: invitationsKey(orgId),
    queryFn: ({ signal }) => invitationsApi.listPending(signal),
  });
}

export function useCreateInvitation(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: invitationsApi.create,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: invitationsKey(orgId) }),
  });
}

export function useRevokeInvitation(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: invitationsApi.revoke,
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: invitationsKey(orgId) }),
  });
}

export function useMembers(orgId: string) {
  return useQuery({
    queryKey: membersKey(orgId),
    queryFn: ({ signal }) => membersApi.list(signal),
  });
}

function useMemberMutation<T>(
  orgId: string,
  mutationFn: (input: T) => Promise<unknown>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    // Refetch either way: on failure the controls snap back to the server's truth, and the
    // caller's own role may have changed.
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: membersKey(orgId) });
      await queryClient.invalidateQueries({ queryKey: CURRENT_USER_KEY });
    },
  });
}

export const useChangeMemberRole = (orgId: string) =>
  useMemberMutation(orgId, membersApi.changeRole);
export const useDeactivateMember = (orgId: string) =>
  useMemberMutation(orgId, membersApi.deactivate);
