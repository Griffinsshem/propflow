"use client";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import {
  usePendingInvitations,
  useRevokeInvitation,
} from "@/features/team/hooks";
import { ROLE_LABELS } from "@/features/team/policy";
import { messageOf } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";

export function PendingInvitations({
  organizationId,
}: {
  organizationId: string;
}) {
  const invitations = usePendingInvitations(organizationId);
  const revoke = useRevokeInvitation(organizationId);

  if (invitations.isPending)
    return <p className="text-sm text-slate-500">Loading…</p>;
  if (invitations.isError)
    return <FormAlert>{messageOf(invitations.error)}</FormAlert>;

  const { items, next_cursor: more } = invitations.data;
  if (items.length === 0)
    return <p className="text-sm text-slate-500">No pending invitations.</p>;

  return (
    <div className="space-y-3">
      {revoke.isError ? <FormAlert>{messageOf(revoke.error)}</FormAlert> : null}
      <ul className="divide-y divide-slate-100">
        {items.map((invitation) => (
          <li
            key={invitation.id}
            className="flex items-center justify-between gap-4 py-3 text-sm"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-slate-900">
                {invitation.email}
              </p>
              <p className="text-slate-500">
                {ROLE_LABELS[invitation.role]} · expires{" "}
                {formatDate(invitation.expires_at)}
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              aria-label={`Revoke invitation for ${invitation.email}`}
              pending={revoke.isPending && revoke.variables === invitation.id}
              onClick={() => revoke.mutate(invitation.id)}
            >
              Revoke
            </Button>
          </li>
        ))}
      </ul>
      {more ? (
        <p className="text-sm text-slate-500">
          Showing the first 100 invitations.
        </p>
      ) : null}
    </div>
  );
}
