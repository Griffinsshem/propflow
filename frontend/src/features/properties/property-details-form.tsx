"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { ConflictNotice } from "@/components/ui/conflict-notice";
import { FormAlert } from "@/components/ui/form-alert";
import { propertyKeys, useUpdateProperty } from "@/features/properties/hooks";
import { PropertyFields } from "@/features/properties/property-fields";
import {
  PROPERTY_FIELDS,
  propertyFormValues,
  propertySchema,
  toPropertyChanges,
  type PropertyFormValues,
} from "@/features/properties/schemas";
import { messageOf } from "@/lib/api/errors";
import { propertiesApi, type Property } from "@/lib/api/properties";
import { changedFields, detectStaleConflict, diffValues, mergeKeepingMine } from "@/lib/conflict";
import { applyFieldErrors } from "@/lib/forms";

const LABELS = {
  name: "Name",
  property_type: "Type",
  status: "Status",
  address_line: "Address",
  city: "City",
  region: "Region",
  country_code: "Country",
  description: "Description",
};

export function PropertyDetailsForm({ orgId, property }: { orgId: string; property: Property }) {
  const queryClient = useQueryClient();
  const update = useUpdateProperty(orgId);
  // The version this form's edits are based on; replaced after every save or conflict choice.
  const [base, setBase] = useState(property);
  const [conflict, setConflict] = useState<Property | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<PropertyFormValues>({
    resolver: zodResolver(propertySchema),
    defaultValues: propertyFormValues(property),
  });

  const fetchLatest = () =>
    queryClient.fetchQuery({
      queryKey: propertyKeys.detail(orgId, base.id),
      queryFn: () => propertiesApi.get(base.id),
      staleTime: 0,
    });

  const onSubmit = handleSubmit(async (values) => {
    setNotice(null);
    setFormError(null);
    const changes = diffValues(values, propertyFormValues(base));
    if (Object.keys(changes).length === 0) {
      setNotice("No changes to save.");
      return;
    }
    try {
      const updated = await update.mutateAsync({
        id: base.id,
        version: base.version,
        changes: toPropertyChanges(changes),
      });
      setBase(updated);
      reset(propertyFormValues(updated));
      setNotice("Saved.");
    } catch (error) {
      const latest = await detectStaleConflict(error, base.version, fetchLatest).catch(() => null);
      if (latest) {
        setConflict(latest);
        return;
      }
      if (!applyFieldErrors(error, setError, PROPERTY_FIELDS)) setFormError(messageOf(error));
    }
  });

  function takeTheirs() {
    if (!conflict) return;
    reset(propertyFormValues(conflict));
    setBase(conflict);
    setConflict(null);
  }

  function keepMine() {
    if (!conflict) return;
    reset(mergeKeepingMine(getValues(), propertyFormValues(base), propertyFormValues(conflict)));
    setBase(conflict);
    setConflict(null);
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      {conflict ? (
        <ConflictNotice
          what="property"
          changes={changedFields(propertyFormValues(base), propertyFormValues(conflict), LABELS)}
          onUseTheirs={takeTheirs}
          onKeepMine={keepMine}
        />
      ) : null}
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <PropertyFields register={register} errors={errors} showStatus />
      <div className="flex items-center gap-3">
        <Button type="submit" pending={isSubmitting} disabled={conflict !== null}>
          {isSubmitting ? "Saving…" : "Save details"}
        </Button>
        <p role="status" className="text-sm text-green-700">
          {notice ?? ""}
        </p>
      </div>
    </form>
  );
}
