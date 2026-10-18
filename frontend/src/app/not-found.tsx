import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="max-w-md text-center">
        <Link href="/" className="text-2xl font-bold tracking-tight text-indigo-600">
          PropFlow
        </Link>
        <p className="mt-10 text-sm font-semibold text-indigo-600">404</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          This page doesn&apos;t exist
        </h1>
        <p className="mt-3 text-slate-600">
          The link may be old or mistyped. Here are some ways back:
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className="rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          >
            Go to the home page
          </Link>
          <Link
            href="/dashboard"
            className="rounded-md bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 shadow-sm ring-1 ring-slate-300 hover:bg-slate-50"
          >
            Your dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
