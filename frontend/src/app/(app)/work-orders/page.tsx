"use client";

import Link from "next/link";
import { useState } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import { useContractors } from "@/features/contractors/hooks";
import { isStaff } from "@/features/maintenance/permissions";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { WorkOrderBadges } from "@/features/work-orders/badges";
import { useWorkOrders } from "@/features/work-orders/hooks";
import { locationLabel, WORK_ORDER_STATUS_LABELS } from "@/features/work-orders/labels";
import { messageOf } from "@/lib/api/errors";
import { WORK_ORDER_STATUSES, type WorkOrderStatus } from "@/lib/api/work-orders";
import { formatDay } from "@/lib/format";

const STATUS_FILTER = [
  { value: "", label: "All statuses" },
  ...WORK_ORDER_STATUSES.map((value) => ({ value, label: WORK_ORDER_STATUS_LABELS[value] })),
];

export default function WorkOrdersPage() {
  const membership = useActiveMembership();
  const orgId = membership?.organization_id ?? null;
  const staff = membership ? isStaff(membership.role) : false;
  const [status, setStatus] = useState("");
  const [contractorId, setContractorId] = useState("");
  const [overdue, setOverdue] = useState(false);
  const orders = useWorkOrders(orgId, {
    ...(status ? { status: status as WorkOrderStatus } : {}),
    ...(contractorId ? { contractorId } : {}),
    overdue,
  });
  const contractors = useContractors(staff ? orgId : null, {});

  if (!membership) return <p className="text-sm text-slate-600">Select an organization first.</p>;
  if (membership.role === "tenant") {
    return (
      <p className="text-sm text-slate-600">Work orders are handled by staff and contractors.</p>
    );
  }
  const filtered = Boolean(status || contractorId || overdue);
  const contractorFilter = [
    { value: "", label: "All contractors" },
    ...(contractors.data?.items ?? []).map((item) => ({
      value: item.id,
      label: item.business_name,
    })),
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Work orders</h1>
      <fieldset className="grid items-end gap-4 sm:grid-cols-3">
        <legend className="sr-only">Filter work orders</legend>
        <SelectField
          id="filter-wo-status"
          label="Status"
          options={STATUS_FILTER}
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        />
        {staff ? (
          <SelectField
            id="filter-wo-contractor"
            label="Contractor"
            options={contractorFilter}
            value={contractorId}
            onChange={(event) => setContractorId(event.target.value)}
          />
        ) : null}
        <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={overdue}
            onChange={(event) => setOverdue(event.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-indigo-600"
          />
          Only overdue
        </label>
      </fieldset>
      {orders.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : orders.isError ? (
        <FormAlert>{messageOf(orders.error)}</FormAlert>
      ) : orders.data.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          {filtered
            ? "No work orders match these filters."
            : staff
              ? "No work orders yet. Assign a contractor from a triaged maintenance request."
              : "No jobs assigned to you yet."}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-lg bg-white ring-1 ring-slate-200">
          {orders.data.items.map((order) => (
            <li key={order.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="min-w-0 space-y-1">
                <Link
                  href={`/work-orders/${order.id}`}
                  className="font-semibold text-slate-900 hover:text-indigo-600"
                >
                  {order.request.title}
                </Link>
                <p className="text-sm text-slate-600">
                  {staff ? `${order.contractor.business_name} · ` : ""}
                  {locationLabel(order)}
                  {order.due_date ? ` · due ${formatDay(order.due_date)}` : ""}
                </p>
              </div>
              <WorkOrderBadges order={order} />
            </li>
          ))}
        </ul>
      )}
      {orders.data?.next_cursor ? (
        <p className="text-sm text-slate-500">Showing the 50 most recent work orders.</p>
      ) : null}
    </div>
  );
}
