import { STATUS_LABELS } from "@/features/maintenance/labels";
import { hasControlCharacters } from "@/features/maintenance/schemas";
import { STATUSES, type MaintenanceStatus } from "@/lib/api/maintenance";

export type StatusAction = { label: string; reasonLabel: string | null };

/**
 * Wording only. Which moves exist and who may make them comes from the API's
 * allowed_transitions; reason rules mirror backend/app/maintenance/workflow.py.
 */
const ACTIONS: Record<string, StatusAction> = {
  "submitted>triaged": { label: "Triage", reasonLabel: null },
  "triaged>assigned": { label: "Mark as assigned", reasonLabel: null },
  "assigned>in_progress": { label: "Start work", reasonLabel: null },
  "in_progress>waiting": { label: "Put on hold", reasonLabel: "What is the work waiting for?" },
  "waiting>in_progress": { label: "Resume work", reasonLabel: null },
  "in_progress>resolved": { label: "Mark resolved", reasonLabel: null },
  "resolved>in_progress": { label: "Reopen", reasonLabel: "Why is it being reopened?" },
  "resolved>closed": { label: "Close", reasonLabel: null },
  "submitted>closed": { label: "Close without fixing", reasonLabel: "Why is it being closed?" },
  "triaged>closed": { label: "Close without fixing", reasonLabel: "Why is it being closed?" },
};

export function actionFor(from: MaintenanceStatus, to: MaintenanceStatus): StatusAction {
  return ACTIONS[`${from}>${to}`] ?? { label: `Move to ${STATUS_LABELS[to]}`, reasonLabel: null };
}

/** Workflow order, with closing always last. */
export function orderedMoves(moves: readonly MaintenanceStatus[]): MaintenanceStatus[] {
  const rank = (status: MaintenanceStatus) =>
    status === "closed" ? STATUSES.length : STATUSES.indexOf(status);
  return [...moves].sort((a, b) => rank(a) - rank(b));
}

const MAX_REASON = 1000;

export function reasonProblem(text: string): string | null {
  if (!text) return "Give a reason.";
  if (text.length > MAX_REASON) return `Use at most ${MAX_REASON} characters.`;
  if (hasControlCharacters(text)) return "Remove unsupported characters.";
  return null;
}
