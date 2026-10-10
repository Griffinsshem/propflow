"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard } from "@/components/ui/auth-card";
import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { newPasswordSchema, type NewPasswordValues } from "@/features/account/schemas";
import { accountApi } from "@/lib/api/account";
import { ApiError, messageOf } from "@/lib/api/errors";
import { useHashToken } from "@/lib/hash-token";

const linkClass = "font-semibold text-indigo-600 hover:text-indigo-500";

function InvalidLink() {
  return (
    <AuthCard title="Link unavailable">
      <p className="text-sm text-slate-600">
        This reset link is invalid, has already been used, or has expired.
      </p>
      <p className="text-sm">
        <Link href="/forgot-password" className={linkClass}>
          Request a new link
        </Link>
      </p>
    </AuthCard>
  );
}

export function ResetPasswordForm() {
  const token = useHashToken();
  const queryClient = useQueryClient();
  const [state, setState] = useState<"form" | "done" | "invalid">("form");
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<NewPasswordValues>({
    resolver: zodResolver(newPasswordSchema),
    defaultValues: { password: "", confirm: "" },
  });

  const onSubmit = handleSubmit(async ({ password }) => {
    if (!token) return;
    setFormError(null);
    try {
      await accountApi.resetPassword({ token, newPassword: password });
      queryClient.clear(); // nothing cached from before the change may linger
      setState("done");
    } catch (error) {
      const passwordError =
        error instanceof ApiError ? error.fieldErrors.new_password?.[0] : undefined;
      if (error instanceof ApiError && error.status === 400) setState("invalid");
      else if (passwordError) setError("password", { type: "server", message: passwordError });
      else if (error instanceof ApiError && error.status === 429) {
        setFormError("Too many attempts. Please wait a few minutes and try again.");
      } else setFormError(messageOf(error));
    }
  });

  if (token === undefined) {
    return (
      <AuthCard title="Choose a new password">
        <p className="text-sm text-slate-500">Loading…</p>
      </AuthCard>
    );
  }
  if (token === null || state === "invalid") return <InvalidLink />;
  if (state === "done") {
    return (
      <AuthCard title="Password changed">
        <p role="status" className="text-sm text-slate-700">
          Your password has been changed. Sign in with your new password.
        </p>
        <Link
          href="/login"
          className="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
        >
          Sign in
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password">
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        {formError ? <FormAlert>{formError}</FormAlert> : null}
        <TextField
          id="new-password"
          label="New password"
          type="password"
          autoComplete="new-password"
          hint="At least 12 characters. A passphrase works well."
          error={errors.password?.message}
          {...register("password")}
        />
        <TextField
          id="confirm-password"
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm?.message}
          {...register("confirm")}
        />
        <Button type="submit" className="w-full" pending={isSubmitting}>
          {isSubmitting ? "Changing…" : "Change password"}
        </Button>
      </form>
    </AuthCard>
  );
}
