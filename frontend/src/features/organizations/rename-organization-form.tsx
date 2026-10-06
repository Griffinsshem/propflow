"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { useRenameOrganization } from "@/features/organizations/hooks";
import {
  organizationNameSchema,
  type OrganizationNameValues,
} from "@/features/organizations/schemas";
import { ApiError } from "@/lib/api/errors";
import type { Organization } from "@/lib/api/organizations";

export function RenameOrganizationForm({
  organization,
}: {
  organization: Organization;
}) {
  const rename = useRenameOrganization();
  const [saved, setSaved] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OrganizationNameValues>({
    resolver: zodResolver(organizationNameSchema),
    defaultValues: { name: organization.name },
  });

  const onSubmit = handleSubmit(async ({ name }) => {
    setSaved(false);
    setFormError(null);
    try {
      await rename.mutateAsync({ id: organization.id, name });
      setSaved(true);
    } catch (error) {
      setFormError(
        error instanceof ApiError ? error.message : "Something went wrong.",
      );
    }
  });

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      className="space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <TextField
        id="organization-name"
        label="Organization name"
        autoComplete="organization"
        error={errors.name?.message}
        {...register("name")}
      />
      <div className="flex items-center gap-3">
        <Button type="submit" pending={isSubmitting}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
        <p role="status" className="text-sm text-green-700">
          {saved ? "Saved." : ""}
        </p>
      </div>
    </form>
  );
}
