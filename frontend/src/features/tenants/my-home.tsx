"use client";

import { FormAlert } from "@/components/ui/form-alert";
import { useMyTenancy } from "@/features/tenants/hooks";
import { messageOf } from "@/lib/api/errors";

export function MyHome({ orgId }: { orgId: string }) {
  const tenancy = useMyTenancy(orgId);
  return (
    <section
      aria-labelledby="home-heading"
      className="space-y-1 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      <h2 id="home-heading" className="font-semibold">
        Your home
      </h2>
      {tenancy.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : tenancy.isError ? (
        <FormAlert>{messageOf(tenancy.error)}</FormAlert>
      ) : tenancy.data.unit ? (
        <p className="text-sm text-slate-700">
          {tenancy.data.unit.property_name ?? "Your property"} · Unit {tenancy.data.unit.label}
        </p>
      ) : (
        <p className="text-sm text-slate-600">
          You haven&apos;t been placed in a unit yet. Your property manager will add you.
        </p>
      )}
    </section>
  );
}
