"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { FormAlert } from "@/components/ui/form-alert";
import { TextField } from "@/components/ui/text-field";
import { useBuildings, useCreateBuilding } from "@/features/properties/hooks";
import { messageOf } from "@/lib/api/errors";

type BuildingsSectionProps = {
  orgId: string;
  propertyId: string;
  canEdit: boolean;
};

export function BuildingsSection({
  orgId,
  propertyId,
  canEdit,
}: BuildingsSectionProps) {
  const buildings = useBuildings(orgId, propertyId);
  const create = useCreateBuilding(orgId, propertyId);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Enter a building name.");
      return;
    }
    setError(null);
    try {
      await create.mutateAsync(trimmed);
      setName("");
    } catch (failure) {
      setError(messageOf(failure));
    }
  }

  if (buildings.isPending)
    return <p className="text-sm text-slate-500">Loading…</p>;
  if (buildings.isError)
    return <FormAlert>{messageOf(buildings.error)}</FormAlert>;

  return (
    <div className="space-y-4">
      {buildings.data.length === 0 ? (
        <p className="text-sm text-slate-500">
          No buildings. Units can also belong directly to the property.
        </p>
      ) : (
        <ul
          aria-label="Buildings"
          className="divide-y divide-slate-100 text-sm"
        >
          {buildings.data.map((building) => (
            <li key={building.id} className="py-2">
              {building.name}
            </li>
          ))}
        </ul>
      )}
      {canEdit ? (
        <form
          onSubmit={add}
          noValidate
          className="flex flex-wrap items-end gap-3"
        >
          <TextField
            id="building-name"
            label="Building name"
            className="min-w-48 flex-1"
            value={name}
            error={error ?? undefined}
            onChange={(event) => setName(event.target.value)}
          />
          <Button type="submit" variant="secondary" pending={create.isPending}>
            Add building
          </Button>
        </form>
      ) : null}
    </div>
  );
}
