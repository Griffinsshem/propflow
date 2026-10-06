"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { useRegister } from "@/features/auth/hooks";
import { registerSchema, type RegisterValues } from "@/features/auth/schemas";
import { ApiError } from "@/lib/api/errors";

const FIELDS = ["full_name", "email", "password"] as const;

type RegisterFormProps = {
  /** Locks the email field to this address. */
  email?: string;
  /** Runs after the account is created, instead of redirecting. */
  onSuccess?: () => Promise<void>;
  showLoginLink?: boolean;
};

export function RegisterForm({
  email,
  onSuccess,
  showLoginLink = true,
}: RegisterFormProps) {
  const router = useRouter();
  const registerAccount = useRegister();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: email ?? "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await registerAccount.mutateAsync(values);
    } catch (error) {
      if (!(error instanceof ApiError)) {
        setFormError("Something went wrong. Please try again.");
        return;
      }
      if (error.status === 409) {
        setError("email", { type: "server", message: error.message });
        return;
      }
      if (error.status === 429) {
        setFormError(
          "Too many sign-up attempts from this network. Please try again later.",
        );
        return;
      }
      let placed = false;
      for (const field of FIELDS) {
        const message = error.fieldErrors[field]?.[0];
        if (message) {
          setError(field, { type: "server", message });
          placed = true;
        }
      }
      if (!placed) setFormError(error.message);
      return;
    }
    if (onSuccess) await onSuccess();
    else router.replace("/dashboard");
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <TextField
        id="full_name"
        label="Full name"
        autoComplete="name"
        error={errors.full_name?.message}
        {...register("full_name")}
      />
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
        autoComplete="new-password"
        hint="At least 12 characters. A passphrase works well."
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" pending={isSubmitting} className="w-full">
        {isSubmitting ? "Creating account…" : "Create account"}
      </Button>
      {showLoginLink ? (
        <p className="text-center text-sm text-slate-600">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-semibold text-indigo-600 hover:text-indigo-500"
          >
            Sign in
          </Link>
        </p>
      ) : null}
    </form>
  );
}
