"use client";

import type { FieldErrors, UseFormRegister } from "react-hook-form";

import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { CONTRACTOR_STATUS_LABELS, SPECIALTY_OPTIONS } from "@/features/contractors/labels";
import type { ContractorFormValues } from "@/features/contractors/schemas";
import { CONTRACTOR_STATUSES } from "@/lib/api/contractors";

const STATUS_OPTIONS = CONTRACTOR_STATUSES.map((value) => ({
  value,
  label: CONTRACTOR_STATUS_LABELS[value],
}));

type ContractorFieldsProps = {
  register: UseFormRegister<ContractorFormValues>;
  errors: FieldErrors<ContractorFormValues>;
  showStatus: boolean;
};

export function ContractorFields({ register, errors, showStatus }: ContractorFieldsProps) {
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <TextField
        id="contractor-business"
        label="Business name"
        className="sm:col-span-2"
        error={errors.business_name?.message}
        {...register("business_name")}
      />
      <SelectField
        id="contractor-specialty"
        label="Specialty"
        options={SPECIALTY_OPTIONS}
        error={errors.specialty?.message}
        {...register("specialty")}
      />
      {showStatus ? (
        <SelectField
          id="contractor-status"
          label="Status"
          options={STATUS_OPTIONS}
          error={errors.status?.message}
          {...register("status")}
        />
      ) : (
        <div className="hidden sm:block" />
      )}
      <TextField
        id="contractor-contact"
        label="Contact name (optional)"
        autoComplete="off"
        error={errors.contact_name?.message}
        {...register("contact_name")}
      />
      <TextField
        id="contractor-phone"
        label="Phone (optional)"
        type="tel"
        placeholder="+254712345678"
        error={errors.phone?.message}
        {...register("phone")}
      />
      <TextField
        id="contractor-email"
        label="Email (optional)"
        type="email"
        autoComplete="off"
        className="sm:col-span-2"
        error={errors.email?.message}
        {...register("email")}
      />
    </div>
  );
}
