"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { AppHeader } from "@/features/auth/app-header";
import { useCurrentUser } from "@/features/auth/hooks";
import { ApiError } from "@/lib/api/errors";

/**
 * Signed-in area. This guard is for user experience only: every API call is authorized by
 * the backend, which is the security boundary.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const me = useCurrentUser();
  const signedOut = me.error instanceof ApiError && me.error.status === 401;

  useEffect(() => {
    if (signedOut) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [signedOut, pathname, router]);

  if (me.isPending || signedOut) {
    return <p className="p-8 text-center text-sm text-slate-500">Loading…</p>;
  }
  if (me.isError) {
    return (
      <div className="mx-auto max-w-md p-8 text-center">
        <p className="text-slate-700">We couldn&apos;t load your account.</p>
        <Button type="button" className="mt-4" onClick={() => me.refetch()}>
          Try again
        </Button>
      </div>
    );
  }
  return (
    <div className="min-h-screen">
      <AppHeader user={me.data} />
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
