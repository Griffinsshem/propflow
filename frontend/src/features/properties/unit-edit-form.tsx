"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { ConflictNotice } from "@/components/ui/conflict-notice";
import { FormAlert } from "@/components/ui/form-alert";
import { propertyKeys, useUpdateUnit } from "@/features/properties/hooks";
import { UNIT_STATUS_LABELS } from "@/features/properties/labels";
import {
  toUnitChanges,
  UNIT_FIELDS,
  unitFormValues,
  unitSchema,
  type UnitFormValues,
} from "@/features/properties/schemas";
import { UnitFields } from "@/features/properties/unit-fields";
import { messageOf } from "@/lib/api/errors";
import {
  unitsApi,
  type Building,
  type Unit,
  type UnitStatus,
} from "@/lib/api/properties";
import {
  changedFields,
  detectStaleConflict,
  diffValues,
  mergeKeepingMine,
} from "@/lib/conflict";
import { applyFieldErrors } from "@/lib/forms";

const LABELS = {
  label: "Label",
  building_id: "Building",
  floor: "Floor",
  bedrooms: "Bedrooms",
  status: "Status",
};

type UnitEditFormProps = { orgId: string; unit: Unit; buildings: Building[] };

export function UnitEditForm({ orgId, unit, buildings }: UnitEditFormProps) {
  const queryClient = useQueryClient();
  const update = useUpdateUnit(orgId, unit.property_id);
  const [base, setBase] = useState(unit);
  const [conflict, setConflict] = useState<Unit | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<UnitFormValues>({
    resolver: zodResolver(unitSchema),
    defaultValues: unitFormValues(unit),
  });

  const buildingName = new Map(
    buildings.map((building) => [building.id, building.name]),
  );
  const describe = (field: string, value: unknown) => {
    if (value === null || value === "") return "(none)";
    if (field === "building_id")
      return buildingName.get(String(value)) ?? "(unknown building)";
    if (field === "status") return UNIT_STATUS_LABELS[value as UnitStatus];
    return String(value);
  };

  const fetchLatest = () =>
    queryClient.fetchQuery({
      queryKey: propertyKeys.unit(orgId, base.id),
      queryFn: () => unitsApi.get(base.id),
      staleTime: 0,
    });

  const onSubmit = handleSubmit(async (values) => {
    setNotice(null);
    setFormError(null);
    const changes = diffValues(values, unitFormValues(base));
    if (Object.keys(changes).length === 0) {
      setNotice("No changes to save.");
      return;
    }
    try {
      const updated = await update.mutateAsync({
        id: base.id,
        version: base.version,
        changes: toUnitChanges(changes),
      });
      setBase(updated);
      reset(unitFormValues(updated));
      setNotice("Saved.");
    } catch (error) {
      const latest = await detectStaleConflict(
        error,
        base.version,
        fetchLatest,
      ).catch(() => null);
      if (latest) {
        setConflict(latest);
        return;
      }
      if (!applyFieldErrors(error, setError, UNIT_FIELDS))
        setFormError(messageOf(error));
    }
  });

  function takeTheirs() {
    if (!conflict) return;
    reset(unitFormValues(conflict));
    setBase(conflict);
    setConflict(null);
  }

  function keepMine() {
    if (!conflict) return;
    reset(
      mergeKeepingMine(
        getValues(),
        unitFormValues(base),
        unitFormValues(conflict),
      ),
    );
    setBase(conflict);
    setConflict(null);
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      {conflict ? (
        <ConflictNotice
          what="unit"
          changes={changedFields(
            unitFormValues(base),
            unitFormValues(conflict),
            LABELS,
            describe,
          )}
          onUseTheirs={takeTheirs}
          onKeepMine={keepMine}
        />
      ) : null}
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <UnitFields register={register} errors={errors} buildings={buildings} />
      <div className="flex items-center gap-3">
        <Button
          type="submit"
          pending={isSubmitting}
          disabled={conflict !== null}
        >
          {isSubmitting ? "Saving…" : "Save unit"}
        </Button>
        <p role="status" className="text-sm text-green-700">
          {notice ?? ""}
        </p>
      </div>
    </form>
  );
}
