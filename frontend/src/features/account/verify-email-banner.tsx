"use client";

import { MailWarning } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { accountApi } from "@/lib/api/account";
import { ApiError, messageOf } from "@/lib/api/errors";

export function VerifyEmailBanner({ email }: { email: string }) {
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  async function resend() {
    setState("sending");
    setError(null);
    try {
      await accountApi.resendVerification();
      setState("sent");
    } catch (failure) {
      setError(
        failure instanceof ApiError && failure.status === 429
          ? "Too many requests. Please wait a few minutes and try again."
          : messageOf(failure),
      );
      setState("idle");
    }
  }

  return (
    <section
      aria-label="Email verification"
      className="flex flex-col gap-3 rounded-lg bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex gap-3">
        <MailWarning aria-hidden className="mt-0.5 h-5 w-5 shrink-0" />
        <p>
          Please verify your email address, <strong className="break-all">{email}</strong>, using
          the link we emailed you.
        </p>
      </div>
      <div className="shrink-0">
        {state === "sent" ? (
          <p role="status">We&apos;ve sent a new link.</p>
        ) : (
          <Button type="button" variant="secondary" pending={state === "sending"} onClick={resend}>
            Resend email
          </Button>
        )}
        {error ? (
          <p role="alert" className="mt-2 text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
