"use client";

import Link from "next/link";

import { useCurrentUser } from "@/features/auth/hooks";
import {
  ContractorOverview,
  OperationsOverview,
  OrganizationOverview,
  TenantOverview,
} from "@/features/dashboard/overviews";
import { activeMembership } from "@/features/organizations/membership";
import { MyHome } from "@/features/tenants/my-home";
import { MyJobs } from "@/features/work-orders/my-jobs";
import type { Role } from "@/lib/api/auth";

function RoleDashboard({ role, orgId }: { role: Role; orgId: string }) {
  switch (role) {
    case "owner":
      return (
        <>
          <OrganizationOverview orgId={orgId} />
          <OperationsOverview orgId={orgId} />
        </>
      );
    case "manager":
      return <OperationsOverview orgId={orgId} />;
    case "tenant":
      return (
        <>
          <MyHome orgId={orgId} />
          <TenantOverview orgId={orgId} />
        </>
      );
    case "contractor":
      return (
        <>
          <ContractorOverview orgId={orgId} />
          <MyJobs orgId={orgId} />
        </>
      );
  }
}

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  if (!user) return null;
  const firstName = user.full_name.split(" ")[0];
  const active = activeMembership(user);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Welcome, {firstName}</h1>
      {user.memberships.length === 0 ? (
        <section className="rounded-lg border border-dashed border-slate-300 bg-white p-6">
          <h2 className="font-semibold">No organization yet</h2>
          <p className="mt-1 text-sm text-slate-600">
            Create an organization to start managing properties, or accept an invitation from one.
          </p>
          <Link
            href="/organizations/new"
            className="mt-4 inline-flex rounded-md bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          >
            Create an organization
          </Link>
        </section>
      ) : active ? (
        <>
          <section className="rounded-lg bg-white p-6 ring-1 ring-slate-200">
            <h2 className="font-semibold">{active.organization_name}</h2>
            <p className="mt-1 text-sm text-slate-600">
              You&apos;re signed in as <span className="capitalize">{active.role}</span>.
            </p>
          </section>
          <RoleDashboard role={active.role} orgId={active.organization_id} />
        </>
      ) : (
        <p className="text-sm text-slate-600">
          Choose an organization from the menu at the top to continue.
        </p>
      )}
    </div>
  );
}
