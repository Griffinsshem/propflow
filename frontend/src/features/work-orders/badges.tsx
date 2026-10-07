import { WORK_ORDER_STATUS_LABELS, WORK_ORDER_STATUS_STYLES } from "@/features/work-orders/labels";
import type { WorkOrder } from "@/lib/api/work-orders";

const pill =
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset";

export function WorkOrderBadges({ order }: { order: WorkOrder }) {
  return (
    <span className="flex flex-wrap items-center gap-2">
      <span className={`${pill} ${WORK_ORDER_STATUS_STYLES[order.status]}`}>
        {WORK_ORDER_STATUS_LABELS[order.status]}
      </span>
      {order.is_overdue ? (
        <span className={`${pill} bg-red-50 text-red-700 ring-red-200`}>Overdue</span>
      ) : null}
    </span>
  );
}
