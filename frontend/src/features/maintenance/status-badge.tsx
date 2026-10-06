import { STATUS_LABELS, STATUS_STYLES } from "@/features/maintenance/labels";
import type { MaintenanceStatus } from "@/lib/api/maintenance";

export function StatusBadge({ status }: { status: MaintenanceStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
