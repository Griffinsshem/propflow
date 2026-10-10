"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { AuthCard } from "@/components/ui/auth-card";
import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { CURRENT_USER_KEY, useCurrentUser } from "@/features/auth/hooks";
import { accountApi } from "@/lib/api/account";
import { ApiError, messageOf } from "@/lib/api/errors";
import { useHashToken } from "@/lib/hash-token";

const buttonLink =
  "flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500";

export function VerifyEmailPanel() {
  const token = useHashToken();
  const queryClient = useQueryClient();
  const signedIn = Boolean(useCurrentUser().data);
  const [state, setState] = useState<"ready" | "pending" | "done" | "invalid">("ready");
  const [error, setError] = useState<string | null>(null);

  // A deliberate click, not automatic: nothing happens just because a page was opened.
  async function verify() {
    if (!token) return;
    setState("pending");
    setError(null);
    try {
      await accountApi.verifyEmail(token);
      await queryClient.invalidateQueries({ queryKey: CURRENT_USER_KEY });
      setState("done");
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 400) {
        setState("invalid");
      } else {
        setError(messageOf(failure));
        setState("ready");
      }
    }
  }

  if (token === undefined) {
    return (
      <AuthCard title="Verify your email">
        <p className="text-sm text-slate-500">Loading…</p>
      </AuthCard>
    );
  }
  if (token === null || state === "invalid") {
    return (
      <AuthCard title="Link unavailable">
        <p className="text-sm text-slate-600">
          This verification link is invalid, has already been used, or has expired. Sign in and use
          &ldquo;Resend email&rdquo; on your dashboard to get a new one.
        </p>
        <Link href={signedIn ? "/dashboard" : "/login"} className={buttonLink}>
          {signedIn ? "Go to your dashboard" : "Sign in"}
        </Link>
      </AuthCard>
    );
  }
  if (state === "done") {
    return (
      <AuthCard title="Email verified">
        <p role="status" className="text-sm text-slate-700">
          Your email address is verified. Thank you.
        </p>
        <Link href={signedIn ? "/dashboard" : "/login"} className={buttonLink}>
          {signedIn ? "Go to your dashboard" : "Sign in"}
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Verify your email">
      <p className="text-sm text-slate-600">Confirm that this email address belongs to you.</p>
      {error ? <FormAlert>{error}</FormAlert> : null}
      <Button type="button" className="w-full" pending={state === "pending"} onClick={verify}>
        {state === "pending" ? "Verifying…" : "Verify my email"}
      </Button>
    </AuthCard>
  );
}
