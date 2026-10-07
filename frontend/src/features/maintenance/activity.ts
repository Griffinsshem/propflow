import { STATUS_LABELS } from "@/features/maintenance/labels";
import type { Comment, HistoryEntry } from "@/lib/api/maintenance";

export type ActivityItem =
  | { kind: "status"; key: string; at: string; entry: HistoryEntry }
  | { kind: "comment"; key: string; at: string; comment: Comment };

/**
 * One timeline, oldest first. At equal times a status change comes before a comment, and the
 * sort is stable, so entries the API returned in order stay in order.
 */
export function mergeActivity(history: HistoryEntry[], comments: Comment[]): ActivityItem[] {
  const items: ActivityItem[] = [
    ...history.map((entry, index) => ({
      kind: "status" as const,
      key: `status-${index}`,
      at: entry.created_at,
      entry,
    })),
    ...comments.map((comment) => ({
      kind: "comment" as const,
      key: `comment-${comment.id}`,
      at: comment.created_at,
      comment,
    })),
  ];
  const rank = (item: ActivityItem) => (item.kind === "status" ? 0 : 1);
  return items.sort((a, b) => Date.parse(a.at) - Date.parse(b.at) || rank(a) - rank(b));
}

export function describeStatusChange(entry: HistoryEntry): string {
  const who = entry.changed_by.full_name;
  if (entry.from_status === null) return `${who} reported this issue`;
  return `${who} moved this from ${STATUS_LABELS[entry.from_status]} to ${STATUS_LABELS[entry.to_status]}`;
}
