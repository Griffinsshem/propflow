import Link from "next/link";
import type { ReactNode } from "react";

const tile = "block rounded-lg bg-slate-50 p-4 ring-1 ring-slate-200";

/** A count; linked only when a list can show exactly the items it counts. */
export function StatTile({ label, value, href }: { label: string; value: number; href?: string }) {
  const body = (
    <>
      <span className="block text-2xl font-semibold text-slate-900">{value}</span>
      <span className="block text-sm text-slate-600">{label}</span>
    </>
  );
  return href ? (
    <Link href={href} aria-label={`${label}: ${value}`} className={`${tile} hover:ring-indigo-300`}>
      {body}
    </Link>
  ) : (
    <div className={tile}>{body}</div>
  );
}

export function StatGrid({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="group" aria-label={label} className="grid grid-cols-2 gap-3 sm:grid-cols-5">
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
      className="space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id={id} className="font-semibold">
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
