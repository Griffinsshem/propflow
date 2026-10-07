"use client";

import Link from "next/link";

import { FormAlert } from "@/components/ui/form-alert";
import { WorkOrderBadges } from "@/features/work-orders/badges";
import { useWorkOrders } from "@/features/work-orders/hooks";
import { locationLabel } from "@/features/work-orders/labels";
import { messageOf } from "@/lib/api/errors";
import type { WorkOrder } from "@/lib/api/work-orders";
import { formatDay } from "@/lib/format";

function JobGroup({ title, orders, empty }: { title: string; orders: WorkOrder[]; empty: string }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-slate-900">
        {title} ({orders.length})
      </h3>
      {orders.length === 0 ? (
        <p className="text-sm text-slate-500">{empty}</p>
      ) : (
        <ul aria-label={title} className="divide-y divide-slate-100 text-sm">
          {orders.map((order) => (
            <li key={order.id} className="flex flex-wrap items-center justify-between gap-3 py-2">
              <div>
                <Link
                  href={`/work-orders/${order.id}`}
                  className="font-medium text-indigo-600 hover:text-indigo-500"
                >
                  {order.request.title}
                </Link>
                <p className="text-slate-500">
                  {locationLabel(order)}
                  {order.due_date ? ` · due ${formatDay(order.due_date)}` : ""}
                </p>
              </div>
              <WorkOrderBadges order={order} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The API returns only this contractor's own jobs; nothing here filters by contractor. */
export function MyJobs({ orgId }: { orgId: string }) {
  const orders = useWorkOrders(orgId, {});
  return (
    <section
      aria-labelledby="jobs-heading"
      className="space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      <h2 id="jobs-heading" className="font-semibold">
        Your jobs
      </h2>
      {orders.isPending ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : orders.isError ? (
        <FormAlert>{messageOf(orders.error)}</FormAlert>
      ) : (
        <>
          <JobGroup
            title="Waiting for you"
            orders={orders.data.items.filter((order) => order.status === "assigned")}
            empty="No new jobs."
          />
          <JobGroup
            title="Underway"
            orders={orders.data.items.filter(
              (order) => order.status === "accepted" || order.status === "in_progress",
            )}
            empty="Nothing underway."
          />
          <Link
            href="/work-orders"
            className="inline-block text-sm font-semibold text-indigo-600 hover:text-indigo-500"
          >
            All your work orders
          </Link>
        </>
      )}
    </section>
  );
}
