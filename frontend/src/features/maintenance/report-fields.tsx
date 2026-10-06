"use client";

import type { FieldErrors, UseFormRegister } from "react-hook-form";

import { SelectField } from "@/components/ui/select-field";
import { TextAreaField } from "@/components/ui/textarea-field";
import { TextField } from "@/components/ui/text-field";
import { CATEGORY_OPTIONS, PRIORITY_OPTIONS } from "@/features/maintenance/labels";
import type { ReportValues } from "@/features/maintenance/schemas";

type ReportFieldsProps = {
  register: UseFormRegister<ReportValues>;
  errors: FieldErrors<ReportValues>;
};

export function ReportFields({ register, errors }: ReportFieldsProps) {
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <TextField
        id="report-title"
        label="Title"
        className="sm:col-span-2"
        placeholder="e.g. Leaking pipe under the kitchen sink"
        error={errors.title?.message}
        {...register("title")}
      />
      <SelectField
        id="report-category"
        label="Category"
        options={CATEGORY_OPTIONS}
        error={errors.category?.message}
        {...register("category")}
      />
      <SelectField
        id="report-priority"
        label="Priority"
        options={PRIORITY_OPTIONS}
        error={errors.priority?.message}
        {...register("priority")}
      />
      <p className="-mt-3 text-sm text-slate-500 sm:col-span-2">
        Urgent means a risk to safety or ongoing damage, such as flooding or exposed wiring.
      </p>
      <TextAreaField
        id="report-description"
        label="What's wrong?"
        rows={5}
        className="sm:col-span-2"
        error={errors.description?.message}
        {...register("description")}
      />
      <TextAreaField
        id="report-access"
        label="Access notes (optional)"
        rows={2}
        className="sm:col-span-2"
        placeholder="When can someone come in? Pets, keys, anything to know."
        error={errors.access_notes?.message}
        {...register("access_notes")}
      />
    </div>
  );
}
