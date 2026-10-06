"use client";

import type { FieldErrors, UseFormRegister } from "react-hook-form";

import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { UNIT_STATUS_OPTIONS } from "@/features/properties/labels";
import type { UnitFormValues } from "@/features/properties/schemas";
import type { Building } from "@/lib/api/properties";
import { toOptionalNumber } from "@/lib/forms";

type UnitFieldsProps = {
  register: UseFormRegister<UnitFormValues>;
  errors: FieldErrors<UnitFormValues>;
  buildings: Building[];
};

export function UnitFields({ register, errors, buildings }: UnitFieldsProps) {
  const buildingOptions = [
    { value: "", label: "No building" },
    ...buildings.map((building) => ({
      value: building.id,
      label: building.name,
    })),
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <TextField
        id="unit-label"
        label="Unit label"
        error={errors.label?.message}
        {...register("label")}
      />
      <SelectField
        id="unit-building"
        label="Building"
        options={buildingOptions}
        error={errors.building_id?.message}
        {...register("building_id")}
      />
      <TextField
        id="unit-floor"
        label="Floor"
        type="number"
        inputMode="numeric"
        error={errors.floor?.message}
        {...register("floor", { setValueAs: toOptionalNumber })}
      />
      <TextField
        id="unit-bedrooms"
        label="Bedrooms"
        type="number"
        min={0}
        inputMode="numeric"
        error={errors.bedrooms?.message}
        {...register("bedrooms", { setValueAs: toOptionalNumber })}
      />
      <SelectField
        id="unit-status"
        label="Unit status"
        options={UNIT_STATUS_OPTIONS}
        error={errors.status?.message}
        {...register("status")}
      />
    </div>
  );
}
