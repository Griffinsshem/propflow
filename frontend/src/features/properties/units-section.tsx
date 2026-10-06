"use client";

import Link from "next/link";

import { FormAlert } from "@/components/ui/form-alert";
import { AddUnitForm } from "@/features/properties/add-unit-form";
import { useBuildings, useUnits } from "@/features/properties/hooks";
import { UNIT_STATUS_LABELS } from "@/features/properties/labels";
import { messageOf } from "@/lib/api/errors";

type UnitsSectionProps = {
  orgId: string;
  propertyId: string;
  canEdit: boolean;
};

export function UnitsSection({
  orgId,
  propertyId,
  canEdit,
}: UnitsSectionProps) {
  const units = useUnits(orgId, propertyId);
  const buildings = useBuildings(orgId, propertyId);

  if (units.isPending || buildings.isPending) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }
  if (units.isError) return <FormAlert>{messageOf(units.error)}</FormAlert>;
  if (buildings.isError)
    return <FormAlert>{messageOf(buildings.error)}</FormAlert>;

  const buildingName = new Map(
    buildings.data.map((building) => [building.id, building.name]),
  );
  const sorted = [...units.data.items].sort((a, b) =>
    a.label.localeCompare(b.label, undefined, { numeric: true }),
  );
  const cell = "px-3 py-2";

  return (
    <div className="space-y-4">
      {sorted.length === 0 ? (
        <p className="text-sm text-slate-500">No units yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">Units</caption>
            <thead className="text-slate-500">
              <tr>
                <th scope="col" className={cell}>
                  Unit
                </th>
                <th scope="col" className={cell}>
                  Building
                </th>
                <th scope="col" className={cell}>
                  Floor
                </th>
                <th scope="col" className={cell}>
                  Bedrooms
                </th>
                <th scope="col" className={cell}>
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sorted.map((unit) => (
                <tr key={unit.id}>
                  <td className={`${cell} font-medium`}>
                    {canEdit ? (
                      <Link
                        href={`/properties/${propertyId}/units/${unit.id}`}
                        className="text-indigo-600 hover:text-indigo-500"
                      >
                        {unit.label}
                      </Link>
                    ) : (
                      unit.label
                    )}
                  </td>
                  <td className={cell}>
                    {unit.building_id
                      ? (buildingName.get(unit.building_id) ?? "—")
                      : "—"}
                  </td>
                  <td className={cell}>{unit.floor ?? "—"}</td>
                  <td className={cell}>{unit.bedrooms ?? "—"}</td>
                  <td className={cell}>{UNIT_STATUS_LABELS[unit.status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {units.data.next_cursor ? (
        <p className="text-sm text-slate-500">Showing the first 100 units.</p>
      ) : null}
      {canEdit ? (
        <AddUnitForm
          orgId={orgId}
          propertyId={propertyId}
          buildings={buildings.data}
        />
      ) : null}
    </div>
  );
}
