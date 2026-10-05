"use client";

import { useCurrentUser } from "@/features/auth/hooks";

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  if (!user) return null;
  const firstName = user.full_name.split(" ")[0];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Welcome, {firstName}</h1>
      {user.memberships.length === 0 ? (
        <section className="rounded-lg border border-dashed border-slate-300 bg-white p-6">
          <h2 className="font-semibold">No organization yet</h2>
          <p className="mt-1 text-sm text-slate-600">
            Create an organization or accept an invitation to start managing properties.
          </p>
        </section>
      ) : (
        <section className="rounded-lg bg-white p-6 ring-1 ring-slate-200">
          <h2 className="font-semibold">Your organizations</h2>
          <ul className="mt-3 divide-y divide-slate-100">
            {user.memberships.map((membership) => (
              <li key={membership.organization_id} className="flex justify-between py-2 text-sm">
                <span>{membership.organization_name}</span>
                <span className="capitalize text-slate-500">{membership.role}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
