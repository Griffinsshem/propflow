"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FlaskConical, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { CURRENT_USER_KEY, useLogout } from "@/features/auth/hooks";
import { activeMembership } from "@/features/organizations/membership";
import type { CurrentUser, Role } from "@/lib/api/auth";
import { demoApi } from "@/lib/api/demo";
import { messageOf } from "@/lib/api/errors";

const PEOPLE: { role: Role; label: string }[] = [
  { role: "owner", label: "Owner" },
  { role: "manager", label: "Manager" },
  { role: "tenant", label: "Tenant" },
  { role: "contractor", label: "Contractor" },
];

const EXPIRY = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  hour: "numeric",
  minute: "2-digit",
});

/** Shown on every page inside a private demo (ADR 0021). */
export function DemoBanner({ user }: { user: CurrentUser }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const logout = useLogout();
  const pickerId = useId();
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const role = activeMembership(user)?.role;
  const expires = user.demo_expires_at ? EXPIRY.format(new Date(user.demo_expires_at)) : null;

  async function viewAs(next: Role) {
    setSwitching(true);
    setError(null);
    try {
      const person = await demoApi.viewAs(next);
      queryClient.clear(); // everything shown so far belonged to the previous person
      queryClient.setQueryData(CURRENT_USER_KEY, person);
      router.push("/dashboard");
    } catch (failure) {
      setError(messageOf(failure));
    } finally {
      setSwitching(false);
    }
  }

  return (
    <section aria-label="Demo" className="border-b border-indigo-200 bg-indigo-50 text-indigo-950">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-3 text-sm">
          <FlaskConical aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-indigo-600" />
          <p>
            <strong>Private demo</strong>
            {expires ? `, deleted ${expires}` : null}. Nothing here is real, and no email is ever
            sent.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor={pickerId} className="text-sm font-medium">
            View as
          </label>
          <select
            id={pickerId}
            value={role ?? "owner"}
            disabled={switching}
            onChange={(event) => viewAs(event.target.value as Role)}
            className="rounded-md border-0 bg-white py-1.5 pl-3 pr-8 text-sm ring-1 ring-inset ring-indigo-200 focus:ring-2 focus:ring-indigo-600 disabled:opacity-60"
          >
            {PEOPLE.map((person) => (
              <option key={person.role} value={person.role}>
                {person.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold text-indigo-700 hover:bg-indigo-100"
          >
            <LogOut aria-hidden className="h-4 w-4" />
            Leave the demo
          </button>
        </div>
      </div>
      {error ? (
        <p role="alert" className="mx-auto max-w-6xl px-4 pb-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </section>
  );
}
