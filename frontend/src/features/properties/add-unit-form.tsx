"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { useCreateUnit } from "@/features/properties/hooks";
import {
  EMPTY_UNIT,
  toUnitInput,
  UNIT_FIELDS,
  unitSchema,
  type UnitFormValues,
} from "@/features/properties/schemas";
import { UnitFields } from "@/features/properties/unit-fields";
import { messageOf } from "@/lib/api/errors";
import type { Building } from "@/lib/api/properties";
import { applyFieldErrors } from "@/lib/forms";

type AddUnitFormProps = {
  orgId: string;
  propertyId: string;
  buildings: Building[];
};

export function AddUnitForm({
  orgId,
  propertyId,
  buildings,
}: AddUnitFormProps) {
  const create = useCreateUnit(orgId, propertyId);
  const [added, setAdded] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<UnitFormValues>({
    resolver: zodResolver(unitSchema),
    defaultValues: EMPTY_UNIT,
  });

  const onSubmit = handleSubmit(async (values) => {
    setAdded(null);
    setFormError(null);
    try {
      const unit = await create.mutateAsync({
        ...toUnitInput(values),
        property_id: propertyId,
      });
      setAdded(unit.label);
      reset({ ...EMPTY_UNIT, building_id: values.building_id });
    } catch (error) {
      if (!applyFieldErrors(error, setError, UNIT_FIELDS))
        setFormError(messageOf(error));
    }
  });

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      className="space-y-4 border-t border-slate-100 pt-4"
    >
      <h3 className="text-sm font-semibold text-slate-900">Add a unit</h3>
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <UnitFields register={register} errors={errors} buildings={buildings} />
      <div className="flex items-center gap-3">
        <Button type="submit" variant="secondary" pending={isSubmitting}>
          Add unit
        </Button>
        <p role="status" className="text-sm text-green-700">
          {added ? `Unit ${added} added.` : ""}
        </p>
      </div>
    </form>
  );
}
