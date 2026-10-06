import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/lib/api/errors";

/** Places the API's per-field validation messages on the form; true if any were placed. */
export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
): boolean {
  if (!(error instanceof ApiError)) return false;
  let placed = false;
  for (const field of fields) {
    const message = error.fieldErrors[field]?.[0];
    if (message) {
      setError(field, { type: "server", message });
      placed = true;
    }
  }
  return placed;
}

/** For number inputs: an empty field means "no value", not zero. */
export const toOptionalNumber = (value: unknown): number | null =>
  value === "" || value === null || value === undefined ? null : Number(value);
