import { ChevronRight, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

/**
 * A count; linked only when a list can show exactly the items it counts. Linked tiles look
 * tappable (white, chevron, hover); plain tiles are quieter, so nobody taps a dead end.
 */
export function StatTile({
  label,
  value,
  href,
  icon: Icon,
}: {
  label: string;
  value: number;
  href?: string;
  icon?: LucideIcon;
}) {
  const body = (
    <>
      <span className="flex items-start justify-between gap-2">
        <span className="text-xl font-semibold text-slate-900 sm:text-2xl">{value}</span>
        {Icon ? <Icon aria-hidden className="h-5 w-5 shrink-0 text-slate-400" /> : null}
      </span>
      <span className="mt-1 flex items-center justify-between gap-1 text-sm text-slate-600">
        <span>{label}</span>
        {href ? <ChevronRight aria-hidden className="h-4 w-4 shrink-0 text-indigo-500" /> : null}
      </span>
    </>
  );
  return href ? (
    <Link
      href={href}
      aria-label={`${label}: ${value}`}
      className="block rounded-lg bg-white p-3 ring-1 ring-slate-200 transition hover:shadow-sm hover:ring-indigo-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:p-4"
    >
      {body}
    </Link>
  ) : (
    <div className="block rounded-lg bg-slate-50 p-3 ring-1 ring-slate-100 sm:p-4">{body}</div>
  );
}

export function StatGrid({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      role="group"
      aria-label={label}
      className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 lg:grid-cols-5"
    >
      {children}
    </div>
  );
}

export function DashboardSection({
  id,
  title,
  aside,
  children,
}: {
  id: string;
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      aria-labelledby={id}
      className="space-y-4 rounded-lg bg-white p-4 ring-1 ring-slate-200 sm:space-y-5 sm:p-6"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <h2 id={id} className="font-semibold">
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
