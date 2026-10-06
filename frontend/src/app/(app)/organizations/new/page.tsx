"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { useCreateOrganization } from "@/features/organizations/hooks";
import {
  organizationNameSchema,
  type OrganizationNameValues,
} from "@/features/organizations/schemas";
import { ApiError } from "@/lib/api/errors";

export default function NewOrganizationPage() {
  const router = useRouter();
  const create = useCreateOrganization();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<OrganizationNameValues>({
    resolver: zodResolver(organizationNameSchema),
    defaultValues: { name: "" },
  });

  const onSubmit = handleSubmit(async ({ name }) => {
    setFormError(null);
    try {
      await create.mutateAsync(name);
      router.replace("/dashboard");
    } catch (error) {
      const nameError = error instanceof ApiError ? error.fieldErrors.name?.[0] : undefined;
      if (nameError) {
        setError("name", { type: "server", message: nameError });
      } else if (error instanceof ApiError && error.status === 429) {
        setFormError("You've created several organizations recently. Please try again later.");
      } else {
        setFormError(error instanceof ApiError ? error.message : "Something went wrong.");
      }
    }
  });

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold tracking-tight">Create an organization</h1>
      <p className="mt-1 text-sm text-slate-600">
        An organization holds your properties, team and tenants. You&apos;ll be its owner.
      </p>
      <form
        onSubmit={onSubmit}
        noValidate
        className="mt-6 space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
      >
        {formError ? <FormAlert>{formError}</FormAlert> : null}
        <TextField
          id="organization-name"
          label="Organization name"
          autoComplete="organization"
          error={errors.name?.message}
          {...register("name")}
        />
        <Button type="submit" pending={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create organization"}
        </Button>
      </form>
    </div>
  );
}
