import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <p className="mb-8 text-center text-2xl font-bold tracking-tight text-indigo-600">
          PropFlow
        </p>
        <div className="rounded-xl bg-white p-8 shadow-sm ring-1 ring-slate-200">{children}</div>
      </div>
    </main>
  );
}
