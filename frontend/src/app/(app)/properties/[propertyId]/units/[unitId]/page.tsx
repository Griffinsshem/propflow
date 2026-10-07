"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { useBuildings, useUnit } from "@/features/properties/hooks";
import { canManageUnits } from "@/features/properties/permissions";
import { UnitEditForm } from "@/features/properties/unit-edit-form";
import { UnitTenantSection } from "@/features/tenants/unit-tenant-section";
import { ApiError, messageOf } from "@/lib/api/errors";

export default function UnitPage() {
  const { propertyId, unitId } = useParams<{
    propertyId: string;
    unitId: string;
  }>();
  const membership = useActiveMembership();
  const orgId = membership?.organization_id ?? null;
  const unit = useUnit(orgId, unitId);
  const buildings = useBuildings(orgId ?? "none", propertyId);
  // Shown while the unit is still at the version this user saved.
  const [savedVersion, setSavedVersion] = useState<number | null>(null);

  const backLink = (
    <Link
      href={`/properties/${propertyId}`}
      className="text-sm font-semibold text-indigo-600 hover:text-indigo-500"
    >
      ← Back to property
    </Link>
  );

  if (!membership || orgId === null) {
    return <p className="text-sm text-slate-600">Select an organization first.</p>;
  }
  if (!canManageUnits(membership.role)) {
    return <p className="text-sm text-slate-600">Only owners and managers can edit units.</p>;
  }
  if (unit.isPending || buildings.isPending) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }
  if (unit.isError || buildings.isError) {
    const error = unit.error ?? buildings.error;
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="space-y-4">
        {backLink}
        <FormAlert>
          {notFound ? "This unit doesn't exist, or it isn't visible to you." : messageOf(error)}
        </FormAlert>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="space-y-1">
        {backLink}
        <h1 className="text-2xl font-bold tracking-tight">Unit {unit.data.label}</h1>
      </div>
      <div className="rounded-lg bg-white p-6 ring-1 ring-slate-200">
        <UnitEditForm
          key={`${unit.data.id}:${unit.data.version}`}
          onSaved={setSavedVersion}
          orgId={orgId}
          unit={unit.data}
          buildings={buildings.data}
        />
        <p role="status" className="mt-3 text-sm text-green-700">
          {savedVersion === unit.data.version ? "Saved." : ""}
        </p>
      </div>
      <section
        aria-labelledby="tenant-heading"
        className="space-y-4 rounded-lg bg-white p-6 ring-1 ring-slate-200"
      >
        <h2 id="tenant-heading" className="font-semibold">
          Tenant
        </h2>
        <UnitTenantSection orgId={orgId} unit={unit.data} />
      </section>
    </div>
  );
}
