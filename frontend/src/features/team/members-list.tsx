"use client";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import {
  useChangeMemberRole,
  useDeactivateMember,
  useMembers,
} from "@/features/team/hooks";
import { ROLE_LABELS } from "@/features/team/policy";
import type { Role } from "@/lib/api/auth";
import { messageOf } from "@/lib/api/errors";

const ROLES: Role[] = ["owner", "manager", "tenant", "contractor"];

export function MembersList({
  organizationId,
  currentUserId,
}: {
  organizationId: string;
  currentUserId: string;
}) {
  const members = useMembers(organizationId);
  const changeRole = useChangeMemberRole(organizationId);
  const deactivate = useDeactivateMember(organizationId);
  const failure = changeRole.error ?? deactivate.error;

  if (members.isPending)
    return <p className="text-sm text-slate-500">Loading…</p>;
  if (members.isError) return <FormAlert>{messageOf(members.error)}</FormAlert>;

  return (
    <div className="space-y-3">
      {failure ? <FormAlert>{messageOf(failure)}</FormAlert> : null}
      <ul className="divide-y divide-slate-100">
        {members.data.items.map((member) => {
          const active = member.status === "active";
          const busy = changeRole.isPending || deactivate.isPending;
          return (
            <li
              key={member.id}
              className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-900">
                  {member.full_name}
                  {member.user_id === currentUserId ? " (you)" : ""}
                </p>
                <p className="truncate text-slate-500">
                  {member.email}
                  {active ? "" : " · deactivated"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  aria-label={`Role for ${member.full_name}`}
                  value={member.role}
                  disabled={!active || busy}
                  onChange={(event) =>
                    changeRole.mutate({
                      id: member.id,
                      role: event.target.value as Role,
                    })
                  }
                  className="rounded-md border-0 py-1.5 pl-3 pr-8 text-sm ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-indigo-600 disabled:opacity-60"
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {ROLE_LABELS[role]}
                    </option>
                  ))}
                </select>
                {active ? (
                  <Button
                    type="button"
                    variant="secondary"
                    aria-label={`Deactivate ${member.full_name}`}
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(
                          `Deactivate ${member.full_name}? They will lose access.`,
                        )
                      ) {
                        deactivate.mutate(member.id);
                      }
                    }}
                  >
                    Deactivate
                  </Button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
