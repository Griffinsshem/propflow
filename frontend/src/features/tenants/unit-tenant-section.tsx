"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import { useUnits } from "@/features/properties/hooks";
import { useEndTenancy, useMoveTenant, useTenants } from "@/features/tenants/hooks";
import { InviteTenantForm } from "@/features/tenants/invite-tenant-form";
import { messageOf } from "@/lib/api/errors";
import type { Unit } from "@/lib/api/properties";
import type { Tenant } from "@/lib/api/tenants";
import { formatDate } from "@/lib/format";

function CurrentTenant({ orgId, unit, tenant }: { orgId: string; unit: Unit; tenant: Tenant }) {
  const units = useUnits(orgId, unit.property_id);
  const move = useMoveTenant(orgId);
  const end = useEndTenancy(orgId);
  const [destination, setDestination] = useState("");
  const failure = move.error ?? end.error;
  const unitItems: Unit[] = units.data?.items ?? [];
  const vacant: Unit[] = unitItems
    .filter((candidate: Unit) => candidate.status === "vacant" && candidate.id !== unit.id)
    .sort((a: Unit, b: Unit) => a.label.localeCompare(b.label, undefined, { numeric: true }));

  const details: [string, string][] = [
    ["Name", tenant.full_name],
    ["Email", tenant.email],
    ["Phone", tenant.phone ?? "—"],
    ["Moved in", tenant.move_in_date ? formatDate(tenant.move_in_date) : "—"],
  ];

  return (
    <div className="space-y-5">
      {failure ? <FormAlert>{messageOf(failure)}</FormAlert> : null}
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        {details.map(([term, value]) => (
          <div key={term}>
            <dt className="font-medium text-slate-900">{term}</dt>
            <dd className="text-slate-700">{value}</dd>
          </div>
        ))}
      </dl>
      {vacant.length > 0 ? (
        <div className="flex flex-wrap items-end gap-3">
          <SelectField
            id="move-destination"
            label="Move to unit"
            className="min-w-48 flex-1"
            value={destination}
            onChange={(event) => setDestination(event.target.value)}
            options={[
              { value: "", label: "Choose a vacant unit" },
              ...vacant.map((candidate) => ({ value: candidate.id, label: candidate.label })),
            ]}
          />
          <Button
            type="button"
            variant="secondary"
            disabled={destination === ""}
            pending={move.isPending}
            onClick={() =>
              move.mutate(
                { id: tenant.id, version: tenant.version, changes: { unit_id: destination } },
                { onSuccess: () => setDestination("") },
              )
            }
          >
            Move tenant
          </Button>
        </div>
      ) : (
        <p className="text-sm text-slate-500">No vacant units in this property to move to.</p>
      )}
      <div className="border-t border-slate-100 pt-4">
        <Button
          type="button"
          variant="secondary"
          pending={end.isPending}
          onClick={() => {
            const question = `End ${tenant.full_name}'s tenancy? They lose access and the unit becomes vacant.`;
            if (window.confirm(question)) end.mutate(tenant.id);
          }}
        >
          End tenancy
        </Button>
      </div>
    </div>
  );
}

export function UnitTenantSection({ orgId, unit }: { orgId: string; unit: Unit }) {
  const tenants = useTenants(orgId, { unitId: unit.id });
  if (tenants.isPending) return <p className="text-sm text-slate-500">Loading…</p>;
  if (tenants.isError) return <FormAlert>{messageOf(tenants.error)}</FormAlert>;
  const tenant = tenants.data.items[0];
  return tenant ? (
    <CurrentTenant key={tenant.id} orgId={orgId} unit={unit} tenant={tenant} />
  ) : (
    <InviteTenantForm orgId={orgId} unitId={unit.id} />
  );
}
