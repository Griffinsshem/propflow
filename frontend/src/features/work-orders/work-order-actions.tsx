"use client";

import { useChangeWorkOrderStatus } from "@/features/work-orders/hooks";
import { orderedWorkOrderMoves, workOrderActionFor } from "@/features/work-orders/workflow";
import { WorkflowActions } from "@/features/workflow/workflow-actions";
import type { WorkOrder } from "@/lib/api/work-orders";

export function WorkOrderActions({ orgId, order }: { orgId: string; order: WorkOrder }) {
  const change = useChangeWorkOrderStatus(orgId, order.id);
  return (
    <WorkflowActions
      groupLabel="Work order actions"
      moves={orderedWorkOrderMoves(order.allowed_transitions ?? [])}
      describe={(to) => workOrderActionFor(order.status, to)}
      isSecondary={(to) => to === "declined" || to === "cancelled"}
      busy={change.isPending}
      pendingMove={change.isPending ? (change.variables?.status ?? null) : null}
      conflictNotice="Someone else updated this work order just now. It now shows the latest status and the actions available from there."
      onMove={(to, reason) => change.mutateAsync({ status: to, reason, version: order.version })}
    />
  );
}
