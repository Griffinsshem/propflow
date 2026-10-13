"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import {
  useAssignManager,
  usePropertyManagers,
  useUnassignManager,
} from "@/features/properties/hooks";
import { useMembers } from "@/features/team/hooks";
import { messageOf } from "@/lib/api/errors";

export function ManagersSection({ orgId, propertyId }: { orgId: string; propertyId: string }) {
  const managers = usePropertyManagers(orgId, propertyId);
  const members = useMembers(orgId);
  const assign = useAssignManager(orgId, propertyId);
  const unassign = useUnassignManager(orgId, propertyId);
  const [selected, setSelected] = useState("");

  if (managers.isPending || members.isPending) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }
  if (managers.isError) return <FormAlert>{messageOf(managers.error)}</FormAlert>;
  if (members.isError) return <FormAlert>{messageOf(members.error)}</FormAlert>;

  const assignedIds = new Set(managers.data.map((manager) => manager.membership_id));
  const candidates = members.data.items.filter(
    (member) =>
      member.role === "manager" && member.status === "active" && !assignedIds.has(member.id),
  );
  const failure = assign.error ?? unassign.error;

  return (
    <div className="space-y-4">
      {failure ? <FormAlert>{messageOf(failure)}</FormAlert> : null}
      {managers.data.length === 0 ? (
        <p className="text-sm text-slate-500">
          No managers assigned. Only owners can see this property until you assign one.
        </p>
      ) : (
        <ul aria-label="Assigned managers" className="divide-y divide-slate-100 text-sm">
          {managers.data.map((manager) => (
            <li
              key={manager.membership_id}
              className="flex items-center justify-between gap-3 py-2"
            >
              <span>
                <span className="font-medium text-slate-900">{manager.full_name}</span>{" "}
                <span className="text-slate-500">{manager.email}</span>
              </span>
              <Button
                type="button"
                variant="secondary"
                aria-label={`Unassign ${manager.full_name}`}
                pending={unassign.isPending && unassign.variables === manager.membership_id}
                onClick={() => unassign.mutate(manager.membership_id)}
              >
                Unassign
              </Button>
            </li>
          ))}
        </ul>
      )}
      {candidates.length > 0 ? (
        <div className="flex flex-wrap items-end gap-3">
          <SelectField
            id="assign-manager"
            label="Manager"
            className="min-w-48 flex-1"
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
            options={[
              { value: "", label: "Choose a manager" },
              ...candidates.map((member) => ({
                value: member.id,
                label: member.full_name,
              })),
            ]}
          />
          <Button
            type="button"
            variant="secondary"
            disabled={selected === ""}
            pending={assign.isPending}
            onClick={() => assign.mutate(selected, { onSuccess: () => setSelected("") })}
          >
            Assign
          </Button>
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          {assignedIds.size > 0 ? "Every manager is already assigned. " : ""}
          Invite more managers from the{" "}
          <Link
            href="/settings/team"
            className="font-semibold text-indigo-600 hover:text-indigo-500"
          >
            Team
          </Link>{" "}
          page.
        </p>
      )}
    </div>
  );
}
