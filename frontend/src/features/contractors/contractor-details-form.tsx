"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { ConflictNotice } from "@/components/ui/conflict-notice";
import { FormAlert } from "@/components/ui/form-alert";
import { ContractorFields } from "@/features/contractors/contractor-fields";
import { contractorKeys, useUpdateContractor } from "@/features/contractors/hooks";
import {
  CONTRACTOR_FIELDS,
  contractorFormValues,
  contractorSchema,
  toContractorChanges,
  type ContractorFormValues,
} from "@/features/contractors/schemas";
import { contractorsApi, type Contractor } from "@/lib/api/contractors";
import { messageOf } from "@/lib/api/errors";
import { changedFields, detectStaleConflict, diffValues, mergeKeepingMine } from "@/lib/conflict";
import { applyFieldErrors } from "@/lib/forms";

const LABELS = {
  business_name: "Business name",
  specialty: "Specialty",
  status: "Status",
  contact_name: "Contact",
  phone: "Phone",
  email: "Email",
};

export function ContractorDetailsForm({
  orgId,
  contractor,
}: {
  orgId: string;
  contractor: Contractor;
}) {
  const queryClient = useQueryClient();
  const update = useUpdateContractor(orgId);
  const [base, setBase] = useState(contractor);
  const [conflict, setConflict] = useState<Contractor | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ContractorFormValues>({
    resolver: zodResolver(contractorSchema),
    defaultValues: contractorFormValues(contractor),
  });

  const fetchLatest = () =>
    queryClient.fetchQuery({
      queryKey: contractorKeys.detail(orgId, base.id),
      queryFn: () => contractorsApi.get(base.id),
      staleTime: 0,
    });

  const onSubmit = handleSubmit(async (values) => {
    setNotice(null);
    setFormError(null);
    const changes = diffValues(values, contractorFormValues(base));
    if (Object.keys(changes).length === 0) {
      setNotice("No changes to save.");
      return;
    }
    try {
      const updated = await update.mutateAsync({
        id: base.id,
        version: base.version,
        changes: toContractorChanges(changes),
      });
      setBase(updated);
      reset(contractorFormValues(updated));
      setNotice("Saved.");
    } catch (error) {
      const latest = await detectStaleConflict(error, base.version, fetchLatest).catch(() => null);
      if (latest) {
        setConflict(latest);
        return;
      }
      if (!applyFieldErrors(error, setError, CONTRACTOR_FIELDS)) setFormError(messageOf(error));
    }
  });

  function takeTheirs() {
    if (!conflict) return;
    reset(contractorFormValues(conflict));
    setBase(conflict);
    setConflict(null);
  }

  function keepMine() {
    if (!conflict) return;
    reset(
      mergeKeepingMine(getValues(), contractorFormValues(base), contractorFormValues(conflict)),
    );
    setBase(conflict);
    setConflict(null);
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      {conflict ? (
        <ConflictNotice
          what="contractor"
          changes={changedFields(
            contractorFormValues(base),
            contractorFormValues(conflict),
            LABELS,
          )}
          onUseTheirs={takeTheirs}
          onKeepMine={keepMine}
        />
      ) : null}
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <ContractorFields register={register} errors={errors} showStatus />
      <div className="flex items-center gap-3">
        <Button type="submit" pending={isSubmitting} disabled={conflict !== null}>
          {isSubmitting ? "Saving…" : "Save contractor"}
        </Button>
        <p role="status" className="text-sm text-green-700">
          {notice ?? ""}
        </p>
      </div>
    </form>
  );
}
