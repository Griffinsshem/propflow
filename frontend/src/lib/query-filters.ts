"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

/** A value from the address bar, kept only if it is one of the allowed options. */
export function pick<T extends string>(value: string | null, allowed: readonly T[]): T | "" {
  return value !== null && (allowed as readonly string[]).includes(value) ? (value as T) : "";
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function uuidOrEmpty(value: string | null): string {
  return value !== null && UUID.test(value) ? value : "";
}

/**
 * List filters that live in the address: read once on arrival (so links and reloads work),
 * written back on every change (so filtered views can be bookmarked and shared).
 */
export function useQueryFilters<K extends string>(
  parse: (params: URLSearchParams) => Record<K, string>,
) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState(() => parse(new URLSearchParams(searchParams.toString())));

  function change(key: K, value: string) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    const params = new URLSearchParams();
    for (const [name, chosen] of Object.entries(next) as [string, string][]) {
      if (chosen) params.set(name, chosen);
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  return [filters, change] as const;
}
