"use client";

import { FormAlert } from "@/components/ui/form-alert";
import { useWorkOrderHistory } from "@/features/work-orders/hooks";
import { WORK_ORDER_STATUS_LABELS } from "@/features/work-orders/labels";
import { messageOf } from "@/lib/api/errors";
import type { WorkOrderHistoryEntry } from "@/lib/api/work-orders";
import { formatDateTime } from "@/lib/format";

function describe(entry: WorkOrderHistoryEntry): string {
  const who = entry.changed_by.full_name;
  if (entry.from_status === null) return `${who} created this work order`;
  return `${who} moved this from ${WORK_ORDER_STATUS_LABELS[entry.from_status]} to ${WORK_ORDER_STATUS_LABELS[entry.to_status]}`;
}

export function WorkOrderHistory({ orgId, workOrderId }: { orgId: string; workOrderId: string }) {
  const history = useWorkOrderHistory(orgId, workOrderId);
  if (history.isPending) return <p className="text-sm text-slate-500">Loading history…</p>;
  if (history.isError) return <FormAlert>{messageOf(history.error)}</FormAlert>;
  return (
    <ol aria-label="Work order history" className="space-y-3">
      {history.data.map((entry, index) => (
        <li key={index} className="flex gap-3 text-sm">
          <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-slate-400" />
          <div>
            <p className="text-slate-700">{describe(entry)}</p>
            {entry.reason ? <p className="text-slate-600">Reason: {entry.reason}</p> : null}
            <time dateTime={entry.created_at} className="text-xs text-slate-500">
              {formatDateTime(entry.created_at)}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}
