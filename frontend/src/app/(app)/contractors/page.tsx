"use client";

import Link from "next/link";
import { useState } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import { useContractors } from "@/features/contractors/hooks";
import { SPECIALTY_LABELS, SPECIALTY_OPTIONS } from "@/features/contractors/labels";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { isStaff } from "@/features/maintenance/permissions";
import type { ContractorStatus, Specialty } from "@/lib/api/contractors";
import { messageOf } from "@/lib/api/errors";

const TABS: { value: ContractorStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];
const SPECIALTY_FILTER = [{ value: "", label: "All specialties" }, ...SPECIALTY_OPTIONS];

export default function ContractorsPage() {
  const membership = useActiveMembership();
  const [status, setStatus] = useState<ContractorStatus>("active");
  const [specialty, setSpecialty] = useState("");
  const contractors = useContractors(membership?.organization_id ?? null, {
    status,
    ...(specialty ? { specialty: specialty as Specialty } : {}),
  });

  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  if (!isStaff(membership.role)) {
    return <p className="text-sm text-slate-600">Only owners and managers manage contractors.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Contractors</h1>
        <Link
          href="/contractors/new"
          className="rounded-md bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
        >
          Add contractor
        </Link>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div role="group" aria-label="Contractor status" className="flex gap-2">
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
        <SelectField
          id="filter-specialty"
          label="Specialty"
          className="min-w-48"
          options={SPECIALTY_FILTER}
          value={specialty}
          onChange={(event) => setSpecialty(event.target.value)}
        />
      </div>
      {contractors.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : contractors.isError ? (
        <FormAlert>{messageOf(contractors.error)}</FormAlert>
      ) : contractors.data.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          {specialty
            ? "No contractors match these filters."
            : status === "active"
              ? "No contractors yet. Add the businesses you call for repairs."
              : "No inactive contractors."}
        </p>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {contractors.data.items.map((contractor) => (
            <li key={contractor.id}>
              <Link
                href={`/contractors/${contractor.id}`}
                className="block rounded-lg bg-white p-5 ring-1 ring-slate-200 hover:ring-indigo-300"
              >
                <p className="font-semibold text-slate-900">{contractor.business_name}</p>
                <p className="mt-1 text-sm text-slate-600">
                  {SPECIALTY_LABELS[contractor.specialty]}
                  {contractor.phone ? ` · ${contractor.phone}` : ""}
                  {contractor.has_login ? " · can sign in" : ""}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
