"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch, type UseFormSetError } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import { useCreateMaintenanceRequest } from "@/features/maintenance/hooks";
import { ReportFields } from "@/features/maintenance/report-fields";
import {
  EMPTY_REPORT,
  REPORT_FIELDS,
  reportSchema,
  toMaintenanceInput,
  type ReportValues,
} from "@/features/maintenance/schemas";
import { propertyKeys, useProperties } from "@/features/properties/hooks";
import { useMyTenancy } from "@/features/tenants/hooks";
import { ApiError, messageOf } from "@/lib/api/errors";
import { unitsApi } from "@/lib/api/properties";
import { applyFieldErrors } from "@/lib/forms";

function useSubmitReport(orgId: string, isStaff: boolean) {
  const router = useRouter();
  const create = useCreateMaintenanceRequest(orgId);
  const [formError, setFormError] = useState<string | null>(null);

  async function submit(values: ReportValues, setError: UseFormSetError<ReportValues>) {
    setFormError(null);
    try {
      const request = await create.mutateAsync(toMaintenanceInput(values, isStaff));
      router.replace(`/maintenance/${request.id}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        setFormError("You've reported many issues recently. Please try again later.");
      } else if (!applyFieldErrors(error, setError, REPORT_FIELDS)) {
        setFormError(messageOf(error));
      }
    }
  }

  return { submit, formError };
}

const SUBMIT_LABEL = "Submit report";

export function TenantReportForm({ orgId }: { orgId: string }) {
  const tenancy = useMyTenancy(orgId);
  const { submit, formError } = useSubmitReport(orgId, false);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ReportValues>({
    resolver: zodResolver(reportSchema(false)),
    defaultValues: EMPTY_REPORT,
  });

  if (tenancy.isPending) return <p className="text-sm text-slate-500">Loading…</p>;
  if (tenancy.isError) return <FormAlert>{messageOf(tenancy.error)}</FormAlert>;
  const unit = tenancy.data.unit;
  if (!unit) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
        You haven&apos;t been placed in a unit yet, so issues can&apos;t be reported for your home.
        Ask your property manager to add you to your unit.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit((values) => submit(values, setError))}
      noValidate
      className="space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      <p className="text-sm font-medium text-slate-700">
        Reporting for {unit.property_name ?? "your property"} · Unit {unit.label}
      </p>
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <ReportFields register={register} errors={errors} />
      <Button type="submit" pending={isSubmitting}>
        {isSubmitting ? "Submitting…" : SUBMIT_LABEL}
      </Button>
    </form>
  );
}

export function StaffReportForm({ orgId }: { orgId: string }) {
  const properties = useProperties(orgId, "active");
  const { submit, formError } = useSubmitReport(orgId, true);
  const {
    register,
    handleSubmit,
    setError,
    control,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ReportValues>({
    resolver: zodResolver(reportSchema(true)),
    defaultValues: EMPTY_REPORT,
  });
  const propertyId = useWatch({ control, name: "property_id" });
  const units = useQuery({
    queryKey: propertyKeys.units(orgId, propertyId || "none"),
    queryFn: ({ signal }) => unitsApi.listForProperty(propertyId, signal),
    enabled: propertyId !== "",
  });

  const propertyOptions = [
    { value: "", label: "Choose a property" },
    ...(properties.data?.items ?? []).map((property) => ({
      value: property.id,
      label: property.name,
    })),
  ];
  const unitOptions = [
    { value: "", label: "No specific unit (common area)" },
    ...[...(units.data?.items ?? [])]
      .sort((a, b) => a.label.localeCompare(b.label, undefined, { numeric: true }))
      .map((unit) => ({ value: unit.id, label: unit.label })),
  ];
  const propertyField = register("property_id");

  return (
    <form
      onSubmit={handleSubmit((values) => submit(values, setError))}
      noValidate
      className="space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
    >
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      {properties.isError ? <FormAlert>{messageOf(properties.error)}</FormAlert> : null}
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField
          id="report-property"
          label="Property"
          options={propertyOptions}
          error={errors.property_id?.message}
          {...propertyField}
          onChange={(event) => {
            setValue("unit_id", ""); // a unit from another property must never be sent
            return propertyField.onChange(event);
          }}
        />
        <SelectField
          id="report-unit"
          label="Unit"
          options={unitOptions}
          disabled={propertyId === ""}
          error={errors.unit_id?.message}
          {...register("unit_id")}
        />
      </div>
      <ReportFields register={register} errors={errors} />
      <Button type="submit" pending={isSubmitting}>
        {isSubmitting ? "Submitting…" : SUBMIT_LABEL}
      </Button>
    </form>
  );
}
