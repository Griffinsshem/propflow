"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { useCreateProperty } from "@/features/properties/hooks";
import { canManageProperties } from "@/features/properties/permissions";
import { PropertyFields } from "@/features/properties/property-fields";
import {
  EMPTY_PROPERTY,
  PROPERTY_FIELDS,
  propertySchema,
  toPropertyInput,
  type PropertyFormValues,
} from "@/features/properties/schemas";
import { messageOf } from "@/lib/api/errors";
import { applyFieldErrors } from "@/lib/forms";

export default function NewPropertyPage() {
  const router = useRouter();
  const membership = useActiveMembership();
  const create = useCreateProperty(membership?.organization_id ?? "");
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<PropertyFormValues>({
    resolver: zodResolver(propertySchema),
    defaultValues: EMPTY_PROPERTY,
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const property = await create.mutateAsync(toPropertyInput(values));
      router.replace(`/properties/${property.id}`);
    } catch (error) {
      if (!applyFieldErrors(error, setError, PROPERTY_FIELDS)) setFormError(messageOf(error));
    }
  });

  if (!membership || !canManageProperties(membership.role)) {
    return <p className="text-sm text-slate-600">Only owners can add properties.</p>;
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight">Add a property</h1>
      <form
        onSubmit={onSubmit}
        noValidate
        className="mt-6 space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
      >
        {formError ? <FormAlert>{formError}</FormAlert> : null}
        <PropertyFields register={register} errors={errors} showStatus={false} />
        <Button type="submit" pending={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create property"}
        </Button>
      </form>
    </div>
  );
}
