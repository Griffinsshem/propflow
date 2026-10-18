import type { ReactNode } from "react";
import Link from "next/link";

/** The centred card used by public pages: sign-in, invitations, password and email links. */
export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <p className="mb-8 text-center text-2xl font-bold tracking-tight text-indigo-600">
          <Link href="/" className="hover:opacity-80">
            PropFlow
          </Link>
        </p>
        <div className="space-y-5 rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
          <h1 className="text-xl font-semibold">{title}</h1>
          {children}
        </div>
      </div>
    </main>
  );
}
