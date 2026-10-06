"use client";

import type { FieldErrors, UseFormRegister } from "react-hook-form";

import { SelectField } from "@/components/ui/select-field";
import { TextAreaField } from "@/components/ui/textarea-field";
import { TextField } from "@/components/ui/text-field";
import {
  PROPERTY_STATUS_OPTIONS,
  PROPERTY_TYPE_OPTIONS,
} from "@/features/properties/labels";
import type { PropertyFormValues } from "@/features/properties/schemas";

type PropertyFieldsProps = {
  register: UseFormRegister<PropertyFormValues>;
  errors: FieldErrors<PropertyFormValues>;
  showStatus: boolean;
};

export function PropertyFields({
  register,
  errors,
  showStatus,
}: PropertyFieldsProps) {
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <TextField
        id="property-name"
        label="Property name"
        className="sm:col-span-2"
        error={errors.name?.message}
        {...register("name")}
      />
      <SelectField
        id="property-type"
        label="Type"
        options={PROPERTY_TYPE_OPTIONS}
        error={errors.property_type?.message}
        {...register("property_type")}
      />
      {showStatus ? (
        <SelectField
          id="property-status"
          label="Status"
          options={PROPERTY_STATUS_OPTIONS}
          error={errors.status?.message}
          {...register("status")}
        />
      ) : (
        <div className="hidden sm:block" />
      )}
      <TextField
        id="property-address"
        label="Address"
        autoComplete="street-address"
        className="sm:col-span-2"
        error={errors.address_line?.message}
        {...register("address_line")}
      />
      <TextField
        id="property-city"
        label="City"
        error={errors.city?.message}
        {...register("city")}
      />
      <TextField
        id="property-region"
        label="Region (optional)"
        error={errors.region?.message}
        {...register("region")}
      />
      <TextField
        id="property-country"
        label="Country code"
        maxLength={2}
        error={errors.country_code?.message}
        {...register("country_code")}
      />
      <TextAreaField
        id="property-description"
        label="Description (optional)"
        rows={3}
        className="sm:col-span-2"
        error={errors.description?.message}
        {...register("description")}
      />
    </div>
  );
}
