"use client";

import Link from "next/link";
import { useId } from "react";

import { useActivateOrganization } from "@/features/organizations/hooks";
import type { CurrentUser } from "@/lib/api/auth";

export function OrganizationSwitcher({ user }: { user: CurrentUser }) {
  const activate = useActivateOrganization();
  // The picker appears in the header and in the phone menu: each copy needs its own id.
  const selectId = useId();
  if (user.memberships.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <label htmlFor={selectId} className="sr-only">
        Active organization
      </label>
      <select
        id={selectId}
        value={user.active_organization_id ?? ""}
        disabled={activate.isPending}
        onChange={(event) => activate.mutate(event.target.value)}
        className="max-w-full rounded-md border-0 py-1.5 pl-3 pr-8 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-indigo-600 disabled:opacity-60"
      >
        {user.active_organization_id === null ? (
          <option value="" disabled>
            Select an organization
          </option>
        ) : null}
        {user.memberships.map((membership) => (
          <option key={membership.organization_id} value={membership.organization_id}>
            {membership.organization_name}
          </option>
        ))}
      </select>
      <Link
        href="/organizations/new"
        className="whitespace-nowrap text-sm font-semibold text-indigo-600 hover:text-indigo-500"
      >
        New organization
      </Link>
      {activate.isError ? (
        <p role="alert" className="text-sm text-red-600">
          Couldn&apos;t switch organization.
        </p>
      ) : null}
    </div>
  );
}
