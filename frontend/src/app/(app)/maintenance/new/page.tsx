"use client";

import Link from "next/link";

import { isStaff, canReport } from "@/features/maintenance/permissions";
import { StaffReportForm, TenantReportForm } from "@/features/maintenance/report-forms";
import { useActiveMembership } from "@/features/organizations/use-active-membership";

export default function NewMaintenanceRequestPage() {
  const membership = useActiveMembership();
  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  if (!canReport(membership.role)) {
    return <p className="text-sm text-slate-600">Contractors can&apos;t report new issues.</p>;
  }
  const orgId = membership.organization_id;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="space-y-1">
        <Link
          href="/maintenance"
          className="text-sm font-semibold text-indigo-600 hover:text-indigo-500"
        >
          ← Maintenance
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">Report an issue</h1>
      </div>
      {isStaff(membership.role) ? (
        <StaffReportForm orgId={orgId} />
      ) : (
        <TenantReportForm orgId={orgId} />
      )}
    </div>
  );
}
