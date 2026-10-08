"use client";

import {
  Archive,
  Building2,
  CalendarX,
  CircleCheck,
  ClipboardList,
  Clock,
  DoorOpen,
  Hammer,
  Handshake,
  Hourglass,
  Inbox,
  Send,
  TriangleAlert,
  Users,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import {
  useContractorDashboard,
  useOperationsDashboard,
  useOrganizationDashboard,
  useTenantDashboard,
} from "@/features/dashboard/hooks";
import { DashboardSection, StatGrid, StatTile } from "@/features/dashboard/stat-tile";
import { locationOf } from "@/features/maintenance/labels";
import { StatusBadge } from "@/features/maintenance/status-badge";
import { useProperties } from "@/features/properties/hooks";
import { WorkOrderBadges } from "@/features/work-orders/badges";
import { locationLabel } from "@/features/work-orders/labels";
import { messageOf } from "@/lib/api/errors";
import type { MaintenanceRequest } from "@/lib/api/maintenance";
import type { WorkOrder } from "@/lib/api/work-orders";
import { formatDate, formatDay } from "@/lib/format";

const loading = <p className="text-sm text-slate-500">Loading…</p>;

function RequestList({
  label,
  requests,
  empty,
}: {
  label: string;
  requests: MaintenanceRequest[];
  empty: string;
}) {
  if (requests.length === 0) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <ul aria-label={label} className="divide-y divide-slate-100 text-sm">
      {requests.map((request) => (
        <li key={request.id} className="flex flex-wrap items-center justify-between gap-3 py-2">
          <div>
            <Link
              href={`/maintenance/${request.id}`}
              className="font-medium text-indigo-600 hover:text-indigo-500"
            >
              {request.title}
            </Link>
            <p className="text-slate-500">
              {locationOf(request)} · {formatDate(request.created_at)}
            </p>
          </div>
          <StatusBadge status={request.status} />
        </li>
      ))}
    </ul>
  );
}

function WorkOrderList({
  label,
  orders,
  empty,
}: {
  label: string;
  orders: WorkOrder[];
  empty: string;
}) {
  if (orders.length === 0) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <ul aria-label={label} className="divide-y divide-slate-100 text-sm">
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
              {order.contractor.business_name} · {locationLabel(order)}
              {order.due_date ? ` · due ${formatDay(order.due_date)}` : ""}
            </p>
          </div>
          <WorkOrderBadges order={order} />
        </li>
      ))}
    </ul>
  );
}

export function OrganizationOverview({ orgId }: { orgId: string }) {
  const dashboard = useOrganizationDashboard(orgId);
  return (
    <DashboardSection id="organization-heading" title="Organization">
      {dashboard.isPending ? (
        loading
      ) : dashboard.isError ? (
        <FormAlert>{messageOf(dashboard.error)}</FormAlert>
      ) : (
        <StatGrid label="Organization totals">
          <StatTile
            icon={Building2}
            label="Properties"
            value={dashboard.data.counts.properties}
            href="/properties"
          />
          <StatTile icon={DoorOpen} label="Units" value={dashboard.data.counts.units} />
          <StatTile
            icon={Users}
            label="Active tenants"
            value={dashboard.data.counts.active_tenants}
            href="/tenants"
          />
          <StatTile
            icon={Wrench}
            label="Open requests"
            value={dashboard.data.counts.open_requests}
          />
          <StatTile
            icon={ClipboardList}
            label="Active work orders"
            value={dashboard.data.counts.active_work_orders}
          />
        </StatGrid>
      )}
    </DashboardSection>
  );
}

export function OperationsOverview({ orgId }: { orgId: string }) {
  const [propertyId, setPropertyId] = useState("");
  const properties = useProperties(orgId, "active");
  const dashboard = useOperationsDashboard(orgId, propertyId || null);
  const choices = properties.data?.items ?? [];
  // Request lists can filter by property; work order lists cannot, so their links only
  // appear when the counts cover every property.
  const requestLink = (status: string) =>
    `/maintenance?status=${status}${propertyId ? `&property=${propertyId}` : ""}`;
  const orderLink = (query: string) => (propertyId ? undefined : `/work-orders?${query}`);

  return (
    <DashboardSection
      id="operations-heading"
      title="Operations"
      aside={
        choices.length > 1 ? (
          <SelectField
            id="operations-property"
            label="Property"
            className="min-w-48"
            value={propertyId}
            onChange={(event) => setPropertyId(event.target.value)}
            options={[
              { value: "", label: "All properties" },
              ...choices.map((item) => ({ value: item.id, label: item.name })),
            ]}
          />
        ) : null
      }
    >
      {dashboard.isPending ? (
        loading
      ) : dashboard.isError ? (
        <FormAlert>{messageOf(dashboard.error)}</FormAlert>
      ) : (
        <>
          <StatGrid label="Maintenance requests">
            <StatTile
              icon={Inbox}
              label="New requests"
              value={dashboard.data.requests.new}
              href={requestLink("submitted")}
            />
            <StatTile
              icon={Hammer}
              label="In progress"
              value={dashboard.data.requests.in_progress}
              href={requestLink("in_progress")}
            />
            <StatTile
              icon={Hourglass}
              label="Waiting"
              value={dashboard.data.requests.waiting}
              href={requestLink("waiting")}
            />
            <StatTile
              icon={TriangleAlert}
              label="Urgent and open"
              value={dashboard.data.requests.urgent}
            />
            <StatTile
              icon={CircleCheck}
              label="Resolved this month"
              value={dashboard.data.requests.resolved_this_month}
            />
          </StatGrid>
          <StatGrid label="Work orders">
            <StatTile
              icon={Clock}
              label="Awaiting acceptance"
              value={dashboard.data.work_orders.awaiting_acceptance}
              href={orderLink("status=assigned")}
            />
            <StatTile
              icon={Hammer}
              label="Work in progress"
              value={dashboard.data.work_orders.in_progress}
              href={orderLink("status=in_progress")}
            />
            <StatTile
              icon={CalendarX}
              label="Overdue work orders"
              value={dashboard.data.work_orders.overdue}
              href={orderLink("overdue=1")}
            />
            <StatTile
              icon={CircleCheck}
              label="Completed this month"
              value={dashboard.data.work_orders.completed_this_month}
            />
          </StatGrid>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-900">Recently reported</h3>
              <RequestList
                label="Recently reported"
                requests={dashboard.data.recent_requests}
                empty="Nothing reported yet."
              />
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-900">Overdue work orders</h3>
              <WorkOrderList
                label="Overdue work orders"
                orders={dashboard.data.overdue_work_orders}
                empty="Nothing overdue."
              />
            </div>
          </div>
        </>
      )}
    </DashboardSection>
  );
}

export function TenantOverview({ orgId }: { orgId: string }) {
  const dashboard = useTenantDashboard(orgId);
  return (
    <DashboardSection id="tenant-requests-heading" title="Your requests">
      {dashboard.isPending ? (
        loading
      ) : dashboard.isError ? (
        <FormAlert>{messageOf(dashboard.error)}</FormAlert>
      ) : (
        <>
          <StatGrid label="Your requests by status">
            <StatTile
              icon={Send}
              label="Submitted"
              value={dashboard.data.requests.submitted}
              href="/maintenance?status=submitted"
            />
            <StatTile
              icon={Hammer}
              label="In progress"
              value={dashboard.data.requests.in_progress}
              href="/maintenance?status=in_progress"
            />
            <StatTile
              icon={Hourglass}
              label="Waiting"
              value={dashboard.data.requests.waiting}
              href="/maintenance?status=waiting"
            />
            <StatTile
              icon={CircleCheck}
              label="Resolved"
              value={dashboard.data.requests.resolved}
              href="/maintenance?status=resolved"
            />
            <StatTile
              icon={Archive}
              label="Closed"
              value={dashboard.data.requests.closed}
              href="/maintenance?status=closed"
            />
          </StatGrid>
          <RequestList
            label="Your recent requests"
            requests={dashboard.data.recent_requests}
            empty="You haven't reported any issues yet."
          />
        </>
      )}
    </DashboardSection>
  );
}

export function ContractorOverview({ orgId }: { orgId: string }) {
  const dashboard = useContractorDashboard(orgId);
  return (
    <DashboardSection id="workload-heading" title="Your workload">
      {dashboard.isPending ? (
        loading
      ) : dashboard.isError ? (
        <FormAlert>{messageOf(dashboard.error)}</FormAlert>
      ) : (
        <StatGrid label="Your work orders by stage">
          <StatTile
            icon={Clock}
            label="Awaiting acceptance"
            value={dashboard.data.work_orders.awaiting_acceptance}
            href="/work-orders?status=assigned"
          />
          <StatTile
            icon={Handshake}
            label="Accepted"
            value={dashboard.data.work_orders.accepted}
            href="/work-orders?status=accepted"
          />
          <StatTile
            icon={Hammer}
            label="In progress"
            value={dashboard.data.work_orders.in_progress}
            href="/work-orders?status=in_progress"
          />
          <StatTile
            icon={CalendarX}
            label="Overdue"
            value={dashboard.data.work_orders.overdue}
            href="/work-orders?overdue=1"
          />
          <StatTile
            icon={CircleCheck}
            label="Completed this month"
            value={dashboard.data.work_orders.completed_this_month}
          />
        </StatGrid>
      )}
    </DashboardSection>
  );
}
