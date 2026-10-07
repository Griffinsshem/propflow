"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { SelectField } from "@/components/ui/select-field";
import { TextAreaField } from "@/components/ui/textarea-field";
import { TextField } from "@/components/ui/text-field";
import { useContractors } from "@/features/contractors/hooks";
import { SPECIALTY_LABELS } from "@/features/contractors/labels";
import { PRIORITY_OPTIONS } from "@/features/maintenance/labels";
import { useCreateWorkOrder } from "@/features/work-orders/hooks";
import {
  ASSIGN_FIELDS,
  assignSchema,
  todayIso,
  toWorkOrderInput,
  type AssignValues,
} from "@/features/work-orders/schemas";
import { messageOf } from "@/lib/api/errors";
import type { MaintenanceRequest } from "@/lib/api/maintenance";
import { applyFieldErrors } from "@/lib/forms";

export function AssignContractorForm({
  orgId,
  request,
}: {
  orgId: string;
  request: MaintenanceRequest;
}) {
  const contractors = useContractors(orgId, { status: "active" });
  const create = useCreateWorkOrder(orgId);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<AssignValues>({
    resolver: zodResolver(assignSchema),
    defaultValues: { contractor_id: "", priority: request.priority, due_date: "", description: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await create.mutateAsync(toWorkOrderInput(request.id, values));
    } catch (error) {
      if (!applyFieldErrors(error, setError, ASSIGN_FIELDS)) setFormError(messageOf(error));
    }
  });

  if (contractors.isPending) return <p className="text-sm text-slate-500">Loading contractors…</p>;
  if (contractors.isError) return <FormAlert>{messageOf(contractors.error)}</FormAlert>;
  if (contractors.data.items.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        No active contractors yet.{" "}
        <Link
          href="/contractors/new"
          className="font-semibold text-indigo-600 hover:text-indigo-500"
        >
          Add a contractor
        </Link>{" "}
        to assign this work.
      </p>
    );
  }

  const contractorOptions = [
    { value: "", label: "Choose a contractor" },
    ...contractors.data.items.map((contractor) => ({
      value: contractor.id,
      label: `${contractor.business_name} (${SPECIALTY_LABELS[contractor.specialty]})`,
    })),
  ];

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4 border-t border-slate-100 pt-4">
      <h3 className="text-sm font-semibold text-slate-900">Assign a contractor</h3>
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <div className="grid gap-4 sm:grid-cols-3">
        <SelectField
          id="assign-contractor"
          label="Contractor"
          options={contractorOptions}
          error={errors.contractor_id?.message}
          {...register("contractor_id")}
        />
        <SelectField
          id="assign-priority"
          label="Priority"
          options={PRIORITY_OPTIONS}
          error={errors.priority?.message}
          {...register("priority")}
        />
        <TextField
          id="assign-due"
          label="Due date (optional)"
          type="date"
          min={todayIso()}
          error={errors.due_date?.message}
          {...register("due_date")}
        />
      </div>
      <TextAreaField
        id="assign-instructions"
        label="Instructions (optional)"
        rows={2}
        error={errors.description?.message}
        {...register("description")}
      />
      <Button type="submit" pending={isSubmitting}>
        {isSubmitting ? "Assigning…" : "Assign contractor"}
      </Button>
    </form>
  );
}
