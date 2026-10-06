import type { Role } from "./auth";
import { apiRequest } from "./client";
import type { Organization } from "./organizations";
import type { Page } from "./pagination";

export type Invitation = {
  id: string;
  email: string;
  role: Role;
  invited_by_user_id: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
};

export type InvitationPreview = {
  organization_name: string;
  role: Role;
  email: string;
  expires_at: string;
};

export const invitationsApi = {
  listPending: (signal?: AbortSignal) =>
    apiRequest<Page<Invitation>>("/invitations?limit=100", { signal }),
  create: (body: { email: string; role: Role }) =>
    apiRequest<Invitation>("/invitations", { method: "POST", body }),
  revoke: (id: string) =>
    apiRequest<Invitation>(`/invitations/${encodeURIComponent(id)}/revoke`, {
      method: "POST",
    }),
  // Tokens travel in request bodies, never in URLs that servers could log.
  preview: (token: string) =>
    apiRequest<InvitationPreview>("/invitations/preview", {
      method: "POST",
      body: { token },
    }),
  accept: (token: string) =>
    apiRequest<Organization>("/invitations/accept", {
      method: "POST",
      body: { token },
    }),
};
