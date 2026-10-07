"use client";

import Link from "next/link";

import { FormAlert } from "@/components/ui/form-alert";
import { AssignContractorForm } from "@/features/work-orders/assign-contractor-form";
import { WorkOrderBadges } from "@/features/work-orders/badges";
import { useWorkOrders } from "@/features/work-orders/hooks";
import { messageOf } from "@/lib/api/errors";
import type { MaintenanceRequest } from "@/lib/api/maintenance";
import { ACTIVE_WORK_ORDER_STATUSES } from "@/lib/api/work-orders";
import { formatDay } from "@/lib/format";

export function RequestWorkOrders({
  orgId,
  request,
}: {
  orgId: string;
  request: MaintenanceRequest;
}) {
  const orders = useWorkOrders(orgId, { requestId: request.id });
  if (orders.isPending) return <p className="text-sm text-slate-500">Loading work orders…</p>;
  if (orders.isError) return <FormAlert>{messageOf(orders.error)}</FormAlert>;

  const items = orders.data.items;
  const hasActive = items.some((order) => ACTIVE_WORK_ORDER_STATUSES.includes(order.status));
  const assignable = request.status === "triaged" || request.status === "assigned";

  return (
    <div className="space-y-4">
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">No work orders yet.</p>
      ) : (
        <ul aria-label="Work orders" className="divide-y divide-slate-100 text-sm">
          {items.map((order) => (
            <li key={order.id} className="flex flex-wrap items-center justify-between gap-3 py-2">
              <div>
                <Link
                  href={`/work-orders/${order.id}`}
                  className="font-medium text-indigo-600 hover:text-indigo-500"
                >
                  {order.contractor.business_name}
                </Link>
                <p className="text-slate-500">
                  {order.due_date ? `Due ${formatDay(order.due_date)}` : "No due date"}
                </p>
              </div>
              <WorkOrderBadges order={order} />
            </li>
          ))}
        </ul>
      )}
      {hasActive ? null : assignable ? (
        <AssignContractorForm orgId={orgId} request={request} />
      ) : request.status === "submitted" ? (
        <p className="text-sm text-slate-600">Triage this request before assigning a contractor.</p>
      ) : null}
    </div>
  );
}
