"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { PRIORITY_LABELS } from "@/features/maintenance/labels";
import { isStaff } from "@/features/maintenance/permissions";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { WorkOrderBadges } from "@/features/work-orders/badges";
import { useWorkOrder } from "@/features/work-orders/hooks";
import { locationLabel } from "@/features/work-orders/labels";
import { WorkOrderActions } from "@/features/work-orders/work-order-actions";
import { WorkOrderHistory } from "@/features/work-orders/work-order-history";
import { ApiError, messageOf } from "@/lib/api/errors";
import { formatDay } from "@/lib/format";

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

const backLink = (
  <Link href="/work-orders" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
    ← Work orders
  </Link>
);

export default function WorkOrderPage() {
  const { workOrderId } = useParams<{ workOrderId: string }>();
  const membership = useActiveMembership();
  const orgId = membership?.organization_id ?? null;
  const order = useWorkOrder(orgId, workOrderId);

  if (!membership || orgId === null) {
    return <p className="text-sm text-slate-600">Select an organization first.</p>;
  }
  if (order.isPending) return <p className="text-sm text-slate-500">Loading…</p>;
  if (order.isError) {
    const notFound = order.error instanceof ApiError && order.error.status === 404;
    return (
      <div className="space-y-4">
        {backLink}
        <FormAlert>
          {notFound
            ? "This work order doesn't exist, or it isn't visible to you."
            : messageOf(order.error)}
        </FormAlert>
      </div>
    );
  }

  const data = order.data;
  const staff = isStaff(membership.role);
  const details: [string, string][] = [
    ["Contractor", data.contractor.business_name],
    ["Priority", PRIORITY_LABELS[data.priority]],
    ["Due date", data.due_date ? formatDay(data.due_date) : "No due date"],
    ["Location", locationLabel(data)],
    ["Address", `${data.location.address_line}, ${data.location.city}`],
  ];

  return (
    <div className="max-w-3xl space-y-6">
      <div className="space-y-2">
        {backLink}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">{data.request.title}</h1>
          <WorkOrderBadges order={data} />
        </div>
      </div>
      <WorkOrderActions orgId={orgId} order={data} />
      <section className="space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          {details.map(([term, value]) => (
            <div key={term}>
              <dt className="font-medium text-slate-900">{term}</dt>
              <dd className="text-slate-700">{value}</dd>
            </div>
          ))}
        </dl>
        {data.description ? (
          <div className="space-y-1 text-sm">
            <h2 className="font-medium text-slate-900">Instructions</h2>
            <p className="whitespace-pre-wrap text-slate-700">{data.description}</p>
          </div>
        ) : null}
        <div className="space-y-1 text-sm">
          <h2 className="font-medium text-slate-900">The reported problem</h2>
          <p className="whitespace-pre-wrap text-slate-700">{data.request.description}</p>
        </div>
        {data.request.access_notes ? (
          <div className="space-y-1 text-sm">
            <h2 className="font-medium text-slate-900">Access notes</h2>
            <p className="whitespace-pre-wrap text-slate-700">{data.request.access_notes}</p>
          </div>
        ) : null}
        {staff ? (
          <Link
            href={`/maintenance/${data.request.id}`}
            className="inline-block text-sm font-semibold text-indigo-600 hover:text-indigo-500"
          >
            Open the maintenance request
          </Link>
        ) : null}
      </section>
      <Section id="history-heading" title="History">
        <WorkOrderHistory orgId={orgId} workOrderId={data.id} />
      </Section>
    </div>
  );
}
