"use client";

import { useChangeStatus } from "@/features/maintenance/status-hooks";
import { actionFor, orderedMoves } from "@/features/maintenance/workflow";
import { WorkflowActions } from "@/features/workflow/workflow-actions";
import type { MaintenanceRequest } from "@/lib/api/maintenance";

export function StatusActions({ orgId, request }: { orgId: string; request: MaintenanceRequest }) {
  const change = useChangeStatus(orgId, request.id);
  return (
    <WorkflowActions
      groupLabel="Status actions"
      moves={orderedMoves(request.allowed_transitions ?? [])}
      describe={(to) => actionFor(request.status, to)}
      isSecondary={(to) => to === "closed"}
      busy={change.isPending}
      pendingMove={change.isPending ? (change.variables?.status ?? null) : null}
      conflictNotice="Someone else updated this request just now. It now shows the latest status and the actions available from there."
      onMove={(to, reason) => change.mutateAsync({ status: to, reason, version: request.version })}
    />
  );
}
