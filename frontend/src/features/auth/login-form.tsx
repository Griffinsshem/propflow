"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { useLogin } from "@/features/auth/hooks";
import { loginSchema, type LoginValues } from "@/features/auth/schemas";
import { ApiError } from "@/lib/api/errors";

type LoginFormProps = {
  next?: string;
  /** Locks the email field to this address. */
  email?: string;
  /** Runs after signing in, instead of redirecting. */
  onSuccess?: () => Promise<void>;
  showRegisterLink?: boolean;
};

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    // One message for both cases: never reveal whether the email or the password was wrong.
    if (error.status === 401) return "Email or password is incorrect.";
    if (error.status === 429) {
      return "Too many sign-in attempts. Please wait a few minutes and try again.";
    }
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

export function LoginForm({
  next = "/dashboard",
  email,
  onSuccess,
  showRegisterLink = true,
}: LoginFormProps) {
  const router = useRouter();
  const login = useLogin();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: email ?? "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login.mutateAsync(values);
    } catch (error) {
      setFormError(loginErrorMessage(error));
      return;
    }
    if (onSuccess) await onSuccess();
    else router.replace(next);
  });

  return (
    <form method="post" onSubmit={onSubmit} noValidate className="space-y-5">
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <TextField
        id="email"
        label="Email"
        type="email"
        autoComplete="email"
        readOnly={email !== undefined}
        error={errors.email?.message}
        {...register("email")}
      />
      <TextField
        id="password"
        label="Password"
        type="password"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register("password")}
      />
      {showRegisterLink ? (
        <div className="-mt-3 text-right">
          <Link
            href="/forgot-password"
            className="text-sm font-semibold text-indigo-600 hover:text-indigo-500"
          >
            Forgot password?
          </Link>
        </div>
      ) : null}
      <Button type="submit" pending={isSubmitting} className="w-full">
        {isSubmitting ? "Signing in…" : "Sign in"}
      </Button>
      {showRegisterLink ? (
        <p className="text-center text-sm text-slate-600">
          New to PropFlow?{" "}
          <Link href="/register" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Create an account
          </Link>
        </p>
      ) : null}
    </form>
  );
}
