"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { BuildingsSection } from "@/features/properties/buildings-section";
import { useProperty } from "@/features/properties/hooks";
import { PROPERTY_STATUS_LABELS, PROPERTY_TYPE_LABELS } from "@/features/properties/labels";
import { ManagersSection } from "@/features/properties/managers-section";
import { canManageProperties, canManageUnits } from "@/features/properties/permissions";
import { PropertyDetailsForm } from "@/features/properties/property-details-form";
import { UnitsSection } from "@/features/properties/units-section";
import { ApiError, messageOf } from "@/lib/api/errors";
import type { Property } from "@/lib/api/properties";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section
      aria-labelledby={id}
      className="space-y-4 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      <h2 id={id} className="font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

function PropertySummary({ property }: { property: Property }) {
  const rows: [string, string][] = [
    ["Type", PROPERTY_TYPE_LABELS[property.property_type]],
    ["Status", PROPERTY_STATUS_LABELS[property.status]],
    ["Address", property.address_line],
    ["City", property.city],
    ["Region", property.region ?? "—"],
    ["Country", property.country_code],
    ["Description", property.description ?? "—"],
  ];
  return (
    <dl className="grid gap-3 text-sm sm:grid-cols-2">
      {rows.map(([term, value]) => (
        <div key={term}>
          <dt className="font-medium text-slate-900">{term}</dt>
          <dd className="text-slate-700">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

const backLink = (
  <Link href="/properties" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
    ← Properties
  </Link>
);

export default function PropertyPage() {
  const { propertyId } = useParams<{ propertyId: string }>();
  const membership = useActiveMembership();
  const orgId = membership?.organization_id ?? null;
  const property = useProperty(orgId, propertyId);

  if (!membership || orgId === null) {
    return <p className="text-sm text-slate-600">Select an organization first.</p>;
  }
  if (property.isPending) return <p className="text-sm text-slate-500">Loading…</p>;
  if (property.isError) {
    const notFound = property.error instanceof ApiError && property.error.status === 404;
    return (
      <div className="space-y-4">
        {backLink}
        <FormAlert>
          {notFound
            ? "This property doesn't exist, or it isn't assigned to you."
            : messageOf(property.error)}
        </FormAlert>
      </div>
    );
  }

  const data = property.data;
  const isOwner = canManageProperties(membership.role);
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        {backLink}
        <h1 className="text-2xl font-bold tracking-tight">{data.name}</h1>
        <p className="text-sm text-slate-600">
          {data.address_line}, {data.city}
          {data.status === "archived" ? " · Archived" : ""}
        </p>
      </div>
      <Section id="details-heading" title="Details">
        {isOwner ? (
          <PropertyDetailsForm key={data.id} orgId={orgId} property={data} />
        ) : (
          <PropertySummary property={data} />
        )}
      </Section>
      <Section id="buildings-heading" title="Buildings">
        <BuildingsSection orgId={orgId} propertyId={data.id} canEdit={isOwner} />
      </Section>
      <Section id="units-heading" title="Units">
        <UnitsSection
          orgId={orgId}
          propertyId={data.id}
          canEdit={canManageUnits(membership.role)}
        />
      </Section>
      {isOwner ? (
        <Section id="managers-heading" title="Managers">
          <ManagersSection orgId={orgId} propertyId={data.id} />
        </Section>
      ) : null}
    </div>
  );
}
