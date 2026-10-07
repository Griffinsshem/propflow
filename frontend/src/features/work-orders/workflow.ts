import type { MoveDescription } from "@/features/workflow/workflow-actions";
import { WORK_ORDER_STATUS_LABELS } from "@/features/work-orders/labels";
import type { WorkOrderStatus } from "@/lib/api/work-orders";

/**
 * Wording only. Which moves exist and who may make them comes from the API's
 * allowed_transitions; reason rules mirror backend/app/work_orders/workflow.py.
 */
const CANCEL: MoveDescription = {
  label: "Cancel work order",
  reasonLabel: "Why is the work order being cancelled?",
};
const ACTIONS: Record<string, MoveDescription> = {
  "assigned>accepted": { label: "Accept job", reasonLabel: null },
  "assigned>declined": { label: "Decline job", reasonLabel: "Why is the job being declined?" },
  "accepted>in_progress": { label: "Start job", reasonLabel: null },
  "in_progress>completed": { label: "Mark job complete", reasonLabel: null },
  "assigned>cancelled": CANCEL,
  "accepted>cancelled": CANCEL,
  "in_progress>cancelled": CANCEL,
};

export function workOrderActionFor(from: WorkOrderStatus, to: WorkOrderStatus): MoveDescription {
  return (
    ACTIONS[`${from}>${to}`] ?? {
      label: `Move to ${WORK_ORDER_STATUS_LABELS[to]}`,
      reasonLabel: null,
    }
  );
}

// Progress first; declining and cancelling last.
const ORDER: WorkOrderStatus[] = [
  "accepted",
  "in_progress",
  "completed",
  "assigned",
  "declined",
  "cancelled",
];

export function orderedWorkOrderMoves(moves: readonly WorkOrderStatus[]): WorkOrderStatus[] {
  return [...moves].sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b));
}
