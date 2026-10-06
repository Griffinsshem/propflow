"use client";

import Link from "next/link";

import { FormAlert } from "@/components/ui/form-alert";
import { useMaintenanceList } from "@/features/maintenance/hooks";
import { locationOf, PRIORITY_LABELS } from "@/features/maintenance/labels";
import { canReport, isStaff } from "@/features/maintenance/permissions";
import { StatusBadge } from "@/features/maintenance/status-badge";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { messageOf } from "@/lib/api/errors";
import { formatDate } from "@/lib/format";

export default function MaintenancePage() {
  const membership = useActiveMembership();
  const requests = useMaintenanceList(membership?.organization_id ?? null, {});

  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  if (!canReport(membership.role)) {
    return (
      <p className="text-sm text-slate-600">Your work orders will appear on your dashboard.</p>
    );
  }
  const staff = isStaff(membership.role);

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
      {requests.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : requests.isError ? (
        <FormAlert>{messageOf(requests.error)}</FormAlert>
      ) : requests.data.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          {staff ? "No maintenance requests yet." : "You haven't reported any issues yet."}
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
