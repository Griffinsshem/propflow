"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard } from "@/components/ui/auth-card";
import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { emailSchema, type EmailValues } from "@/features/account/schemas";
import { accountApi } from "@/lib/api/account";
import { ApiError, messageOf } from "@/lib/api/errors";

const backToSignIn = (
  <p className="text-center text-sm">
    <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
      Back to sign in
    </Link>
  </p>
);

export function ForgotPasswordForm() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EmailValues>({ resolver: zodResolver(emailSchema), defaultValues: { email: "" } });

  const onSubmit = handleSubmit(async ({ email }) => {
    setFormError(null);
    try {
      await accountApi.forgotPassword(email);
      setSentTo(email);
    } catch (error) {
      setFormError(
        error instanceof ApiError && error.status === 429
          ? "Too many reset requests. Please wait a few minutes and try again."
          : messageOf(error),
      );
    }
  });

  if (sentTo) {
    return (
      <AuthCard title="Check your email">
        {/* The same answer whether or not the account exists: nobody can probe for accounts. */}
        <p role="status" className="text-sm text-slate-700">
          If an account exists for <strong className="break-all">{sentTo}</strong>, we&apos;ve sent
          it a link to choose a new password. The link expires, so use it soon.
        </p>
        {backToSignIn}
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Reset your password">
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <p className="text-sm text-slate-600">
          Enter the email address you sign in with, and we&apos;ll send you a link to choose a new
          password.
        </p>
        {formError ? <FormAlert>{formError}</FormAlert> : null}
        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <Button type="submit" className="w-full" pending={isSubmitting}>
          {isSubmitting ? "Sending…" : "Send reset link"}
        </Button>
        {backToSignIn}
      </form>
    </AuthCard>
  );
}
