"use client";

import Link from "next/link";
import { useState } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import { useMaintenanceList } from "@/features/maintenance/hooks";
import {
  locationOf,
  PRIORITY_LABELS,
  PRIORITY_OPTIONS,
  STATUS_LABELS,
} from "@/features/maintenance/labels";
import { canReport, isStaff } from "@/features/maintenance/permissions";
import { StatusBadge } from "@/features/maintenance/status-badge";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { useProperties } from "@/features/properties/hooks";
import { messageOf } from "@/lib/api/errors";
import {
  STATUSES,
  type MaintenanceFilters,
  type MaintenanceStatus,
  type Priority,
} from "@/lib/api/maintenance";
import { formatDate } from "@/lib/format";

const STATUS_FILTER = [
  { value: "", label: "All statuses" },
  ...STATUSES.map((value) => ({ value, label: STATUS_LABELS[value] })),
];
const PRIORITY_FILTER = [{ value: "", label: "All priorities" }, ...PRIORITY_OPTIONS];

export default function MaintenancePage() {
  const membership = useActiveMembership();
  const orgId = membership?.organization_id ?? null;
  const staff = membership ? isStaff(membership.role) : false;
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [propertyId, setPropertyId] = useState("");
  const filters: MaintenanceFilters = {
    ...(status ? { status: status as MaintenanceStatus } : {}),
    ...(priority ? { priority: priority as Priority } : {}),
    ...(propertyId ? { propertyId } : {}),
  };
  const requests = useMaintenanceList(orgId, filters);
  const properties = useProperties(staff ? orgId : null, "active");

  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  if (!canReport(membership.role)) {
    return (
      <p className="text-sm text-slate-600">Your work orders will appear on your dashboard.</p>
    );
  }
  const filtered = Boolean(status || priority || propertyId);
  const propertyFilter = [
    { value: "", label: "All properties" },
    ...(properties.data?.items ?? []).map((item) => ({ value: item.id, label: item.name })),
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Maintenance</h1>
        <Link
          href="/maintenance/new"
          className="rounded-md bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
        >
          Report an issue
        </Link>
      </div>
      <fieldset className="grid gap-4 sm:grid-cols-3">
        <legend className="sr-only">Filter requests</legend>
        <SelectField
          id="filter-status"
          label="Status"
          options={STATUS_FILTER}
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        />
        <SelectField
          id="filter-priority"
          label="Priority"
          options={PRIORITY_FILTER}
          value={priority}
          onChange={(event) => setPriority(event.target.value)}
        />
        {staff ? (
          <SelectField
            id="filter-property"
            label="Property"
            options={propertyFilter}
            value={propertyId}
            onChange={(event) => setPropertyId(event.target.value)}
          />
        ) : null}
      </fieldset>
      {requests.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : requests.isError ? (
        <FormAlert>{messageOf(requests.error)}</FormAlert>
      ) : requests.data.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          {filtered
            ? "No requests match these filters."
            : staff
              ? "No maintenance requests yet."
              : "You haven't reported any issues yet."}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-lg bg-white ring-1 ring-slate-200">
          {requests.data.items.map((request) => (
            <li key={request.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="min-w-0 space-y-1">
                <Link
                  href={`/maintenance/${request.id}`}
                  className="font-semibold text-slate-900 hover:text-indigo-600"
                >
                  {request.title}
                </Link>
                <p className="text-sm text-slate-600">
                  {locationOf(request)}
                  {staff ? ` · reported by ${request.reported_by.full_name}` : ""} ·{" "}
                  {formatDate(request.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-3 text-sm text-slate-600">
                <span>{PRIORITY_LABELS[request.priority]}</span>
                <StatusBadge status={request.status} />
              </div>
            </li>
          ))}
        </ul>
      )}
      {requests.data?.next_cursor ? (
        <p className="text-sm text-slate-500">Showing the 50 most recent requests.</p>
      ) : null}
    </div>
  );
}
