import { z } from "zod";

import { CATEGORIES, PRIORITIES, type MaintenanceInput } from "@/lib/api/maintenance";

/** Mirrors the API's plain_text rule: printable text plus newlines and tabs only. */
export function hasControlCharacters(value: string): boolean {
  for (const character of value) {
    const code = character.charCodeAt(0);
    const allowedWhitespace = character === "\n" || character === "\r" || character === "\t";
    if ((code < 32 && !allowedWhitespace) || code === 127) return true;
  }
  return false;
}

const plainText = (schema: z.ZodString) =>
  schema.refine((value) => !hasControlCharacters(value), "Remove unsupported characters.");

// Mirrors the API's rules (backend/app/maintenance/schemas.py); the API remains the authority.
export function reportSchema(requireProperty: boolean) {
  return z.object({
    title: plainText(
      z
        .string()
        .trim()
        .min(3, "Use at least 3 characters.")
        .max(150, "Use at most 150 characters."),
    ),
    category: z.enum(CATEGORIES),
    priority: z.enum(PRIORITIES),
    description: plainText(
      z.string().trim().min(1, "Describe the problem.").max(5000, "Use at most 5000 characters."),
    ),
    access_notes: plainText(z.string().trim().max(1000, "Use at most 1000 characters.")),
    property_id: requireProperty ? z.string().min(1, "Choose a property.") : z.string(),
    unit_id: z.string(),
  });
}

export type ReportValues = z.infer<ReturnType<typeof reportSchema>>;

export const REPORT_FIELDS = [
  "title",
  "category",
  "priority",
  "description",
  "access_notes",
  "property_id",
  "unit_id",
] as const;

export const EMPTY_REPORT: ReportValues = {
  title: "",
  category: "plumbing",
  priority: "normal",
  description: "",
  access_notes: "",
  property_id: "",
  unit_id: "",
};

export function toMaintenanceInput(values: ReportValues, isStaff: boolean): MaintenanceInput {
  const input: MaintenanceInput = {
    title: values.title,
    category: values.category,
    priority: values.priority,
    description: values.description,
    access_notes: values.access_notes || null,
  };
  if (!isStaff) return input; // the API locates tenants' reports from their tenant profile
  return {
    ...input,
    property_id: values.property_id,
    ...(values.unit_id ? { unit_id: values.unit_id } : {}),
  };
}
