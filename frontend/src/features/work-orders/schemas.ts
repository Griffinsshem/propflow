import { z } from "zod";

import { hasControlCharacters } from "@/features/maintenance/schemas";
import { PRIORITIES } from "@/lib/api/maintenance";
import type { WorkOrderInput } from "@/lib/api/work-orders";

/** Today as YYYY-MM-DD in the user's own time zone. */
export function todayIso(): string {
  return new Date().toLocaleDateString("en-CA");
}

export const assignSchema = z.object({
  contractor_id: z.string().min(1, "Choose a contractor."),
  priority: z.enum(PRIORITIES),
  due_date: z
    .string()
    .refine((value) => value === "" || (/^\d{4}-\d{2}-\d{2}$/.test(value) && value >= todayIso()), {
      message: "Choose today or a later date.",
    }),
  description: z
    .string()
    .trim()
    .max(2000, "Use at most 2000 characters.")
    .refine((value) => !hasControlCharacters(value), "Remove unsupported characters."),
});

export type AssignValues = z.infer<typeof assignSchema>;

export const ASSIGN_FIELDS = ["contractor_id", "priority", "due_date", "description"] as const;

export function toWorkOrderInput(requestId: string, values: AssignValues): WorkOrderInput {
  return {
    request_id: requestId,
    contractor_id: values.contractor_id,
    priority: values.priority,
    description: values.description || null,
    due_date: values.due_date || null,
  };
}
