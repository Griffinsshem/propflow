"use client";

import Link from "next/link";

import { FormAlert } from "@/components/ui/form-alert";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { canManageUnits } from "@/features/properties/permissions";
import { useTenants } from "@/features/tenants/hooks";
import { messageOf } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";

export default function TenantsPage() {
  const membership = useActiveMembership();
  const tenants = useTenants(membership?.organization_id ?? null, {});

  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  if (!canManageUnits(membership.role)) {
    return <p className="text-sm text-slate-600">Only owners and managers can see tenants.</p>;
  }

  const cell = "px-3 py-2";
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Tenants</h1>
      {tenants.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : tenants.isError ? (
        <FormAlert>{messageOf(tenants.error)}</FormAlert>
      ) : tenants.data.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          No tenants yet. Invite a tenant from a vacant unit&apos;s page.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg bg-white ring-1 ring-slate-200">
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">Tenants</caption>
            <thead className="text-slate-500">
              <tr>
                <th scope="col" className={cell}>
                  Tenant
                </th>
                <th scope="col" className={cell}>
                  Home
                </th>
                <th scope="col" className={cell}>
                  Moved in
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tenants.data.items.map((tenant) => (
                <tr key={tenant.id}>
                  <td className={cell}>
                    <p className="font-medium text-slate-900">{tenant.full_name}</p>
                    <p className="text-slate-500">{tenant.email}</p>
                  </td>
                  <td className={cell}>
                    {tenant.unit ? (
                      <Link
                        href={`/properties/${tenant.unit.property_id}/units/${tenant.unit.id}`}
                        className="text-indigo-600 hover:text-indigo-500"
                      >
                        {tenant.unit.property_name ?? "Property"} · Unit {tenant.unit.label}
                      </Link>
                    ) : (
                      <span className="text-slate-500">Not placed</span>
                    )}
                  </td>
                  <td className={cell}>
                    {tenant.move_in_date ? formatDate(tenant.move_in_date) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {tenants.data?.next_cursor ? (
        <p className="text-sm text-slate-500">Showing the first 100 tenants.</p>
      ) : null}
    </div>
  );
}
