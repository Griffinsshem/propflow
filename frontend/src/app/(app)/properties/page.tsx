"use client";

import Link from "next/link";
import { useState } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { useProperties } from "@/features/properties/hooks";
import { PROPERTY_TYPE_LABELS } from "@/features/properties/labels";
import { canManageProperties } from "@/features/properties/permissions";
import { messageOf } from "@/lib/api/errors";
import type { PropertyStatus } from "@/lib/api/properties";

const TABS: { value: PropertyStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
];

export default function PropertiesPage() {
  const membership = useActiveMembership();
  const [status, setStatus] = useState<PropertyStatus>("active");
  const properties = useProperties(membership?.organization_id ?? null, status);

  if (!membership)
    return (
      <p className="text-sm text-slate-600">Select an organization first.</p>
    );
  const isOwner = canManageProperties(membership.role);

  function emptyMessage(): string {
    if (status === "archived") return "No archived properties.";
    return isOwner
      ? "No properties yet. Add your first property to start organizing units and tenants."
      : "No properties are assigned to you yet. An owner can assign you to a property.";
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Properties</h1>
        {isOwner ? (
          <Link
            href="/properties/new"
            className="rounded-md bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          >
            Add property
          </Link>
        ) : null}
      </div>
      <div role="group" aria-label="Property status" className="flex gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            aria-pressed={status === tab.value}
            onClick={() => setStatus(tab.value)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              status === tab.value
                ? "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {properties.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : properties.isError ? (
        <FormAlert>{messageOf(properties.error)}</FormAlert>
      ) : properties.data.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          {emptyMessage()}
        </p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {properties.data.items.map((property) => (
            <li key={property.id}>
              <Link
                href={`/properties/${property.id}`}
                className="block rounded-lg bg-white p-5 ring-1 ring-slate-200 hover:ring-indigo-300"
              >
                <p className="font-semibold text-slate-900">{property.name}</p>
                <p className="mt-1 text-sm text-slate-600">
                  {PROPERTY_TYPE_LABELS[property.property_type]} ·{" "}
                  {property.city}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
