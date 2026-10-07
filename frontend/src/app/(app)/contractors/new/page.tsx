"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { ContractorFields } from "@/features/contractors/contractor-fields";
import { useCreateContractor } from "@/features/contractors/hooks";
import {
  CONTRACTOR_FIELDS,
  contractorSchema,
  EMPTY_CONTRACTOR,
  toContractorInput,
  type ContractorFormValues,
} from "@/features/contractors/schemas";
import { isStaff } from "@/features/maintenance/permissions";
import { useActiveMembership } from "@/features/organizations/use-active-membership";
import { messageOf } from "@/lib/api/errors";
import { applyFieldErrors } from "@/lib/forms";

export default function NewContractorPage() {
  const router = useRouter();
  const membership = useActiveMembership();
  const create = useCreateContractor(membership?.organization_id ?? "");
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ContractorFormValues>({
    resolver: zodResolver(contractorSchema),
    defaultValues: EMPTY_CONTRACTOR,
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const contractor = await create.mutateAsync(toContractorInput(values));
      router.replace(`/contractors/${contractor.id}`);
    } catch (error) {
      if (!applyFieldErrors(error, setError, CONTRACTOR_FIELDS)) setFormError(messageOf(error));
    }
  });

  if (!membership || !isStaff(membership.role)) {
    return <p className="text-sm text-slate-600">Only owners and managers add contractors.</p>;
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight">Add a contractor</h1>
      <form
        onSubmit={onSubmit}
        noValidate
        className="mt-6 space-y-5 rounded-lg bg-white p-6 ring-1 ring-slate-200"
      >
        {formError ? <FormAlert>{formError}</FormAlert> : null}
        <ContractorFields register={register} errors={errors} showStatus={false} />
        <Button type="submit" pending={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create contractor"}
        </Button>
      </form>
    </div>
  );
}
