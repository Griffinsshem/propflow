"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { CURRENT_USER_KEY } from "@/features/auth/hooks";
import { demoApi } from "@/lib/api/demo";
import { ApiError, messageOf } from "@/lib/api/errors";

export function StartDemoButton({ className = "" }: { className?: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const user = await demoApi.start();
      queryClient.clear(); // nothing from a previous visit may leak into the demo
      queryClient.setQueryData(CURRENT_USER_KEY, user);
      router.push("/dashboard");
    } catch (failure) {
      setError(
        failure instanceof ApiError && failure.status === 429
          ? "You've started several demos recently. Please try again in an hour, or create a free account."
          : messageOf(failure),
      );
      setStarting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={start}
        disabled={starting}
        aria-describedby={starting ? "demo-starting" : undefined}
        className={`${className} disabled:cursor-wait disabled:opacity-80`}
      >
        <Sparkles aria-hidden className="h-4 w-4" />
        {starting ? "Preparing your demo…" : "Try the live demo"}
      </button>
      <p id="demo-starting" role="status" className="basis-full text-sm text-slate-500">
        {starting ? "This can take up to a minute if the server is waking up." : ""}
      </p>
      {error ? (
        <p role="alert" className="basis-full text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </>
  );
}
