/**
 * Optimistic-concurrency helpers (ADR 0006): saves send only changed fields plus the version
 * the user started from; a 409 caused by someone else's save becomes an explicit choice.
 */
import { ApiError } from "@/lib/api/errors";

export type FieldChange = { field: string; label: string; value: string };

type Values = Record<string, unknown>;

const show = (value: unknown) => (value === null || value === "" ? "(empty)" : String(value));

/** The labelled fields whose value differs between two versions, in `labels` order. */
export function changedFields<T extends Values>(
  before: T,
  after: T,
  labels: Partial<Record<keyof T & string, string>>,
  format: (field: string, value: unknown) => string = (_field, value) => show(value),
): FieldChange[] {
  return Object.entries(labels).flatMap(([field, label]) =>
    label === undefined || before[field] === after[field]
      ? []
      : [{ field, label, value: format(field, after[field]) }],
  );
}

/** Only the fields whose value differs from `base`: what a save should send. */
export function diffValues<T extends Values>(values: T, base: T): Partial<T> {
  const changes: Partial<T> = {};
  for (const key of Object.keys(values) as (keyof T)[]) {
    if (values[key] !== base[key]) changes[key] = values[key];
  }
  return changes;
}

/** Their latest version, keeping only the fields this user actually edited. */
export function mergeKeepingMine<T extends Values>(mine: T, original: T, latest: T): T {
  const merged = { ...latest };
  for (const key of Object.keys(mine) as (keyof T)[]) {
    if (mine[key] !== original[key]) merged[key] = mine[key];
  }
  return merged;
}

/** If `error` is a 409 caused by someone else's save, the latest version; otherwise null. */
export async function detectStaleConflict<T extends { version: number }>(
  error: unknown,
  baseVersion: number,
  fetchLatest: () => Promise<T>,
): Promise<T | null> {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  const latest = await fetchLatest();
  return latest.version !== baseVersion ? latest : null;
}
