import { z } from "zod";

import {
  PROPERTY_STATUSES,
  PROPERTY_TYPES,
  UNIT_STATUSES,
  type Property,
  type PropertyChanges,
  type PropertyInput,
  type Unit,
  type UnitInput,
} from "@/lib/api/properties";

// Mirrors the API's rules (backend/app/properties/schemas.py); the API remains the authority.
const optionalText = (max: number) => z.string().trim().max(max, `Use at most ${max} characters.`);

export const propertySchema = z.object({
  name: z.string().trim().min(1, "Enter a name.").max(200, "Use at most 200 characters."),
  property_type: z.enum(PROPERTY_TYPES),
  status: z.enum(PROPERTY_STATUSES),
  address_line: z
    .string()
    .trim()
    .min(1, "Enter an address.")
    .max(200, "Use at most 200 characters."),
  city: z.string().trim().min(1, "Enter a city.").max(100, "Use at most 100 characters."),
  region: optionalText(100),
  country_code: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z]{2}$/, "Use a two-letter country code, e.g. KE."),
  description: optionalText(2000),
});

export type PropertyFormValues = z.infer<typeof propertySchema>;

export const PROPERTY_FIELDS = [
  "name",
  "property_type",
  "status",
  "address_line",
  "city",
  "region",
  "country_code",
  "description",
] as const;

export const EMPTY_PROPERTY: PropertyFormValues = {
  name: "",
  property_type: "residential",
  status: "active",
  address_line: "",
  city: "",
  region: "",
  country_code: "KE",
  description: "",
};

export function propertyFormValues(property: Property): PropertyFormValues {
  return {
    name: property.name,
    property_type: property.property_type,
    status: property.status,
    address_line: property.address_line,
    city: property.city,
    region: property.region ?? "",
    country_code: property.country_code,
    description: property.description ?? "",
  };
}

/** Create payload: new properties are always active, so status is not sent. */
export function toPropertyInput(values: PropertyFormValues): PropertyInput {
  return {
    name: values.name,
    property_type: values.property_type,
    address_line: values.address_line,
    city: values.city,
    region: values.region || null,
    country_code: values.country_code,
    description: values.description || null,
  };
}

export function toPropertyChanges(changes: Partial<PropertyFormValues>): PropertyChanges {
  const blankToNull = (key: string, value: unknown) =>
    (key === "region" || key === "description") && value === "" ? null : value;
  return Object.fromEntries(
    Object.entries(changes).map(([key, value]) => [key, blankToNull(key, value)]),
  ) as PropertyChanges;
}

const optionalInteger = (min: number, max: number, name: string) =>
  z
    .number()
    .int("Use a whole number.")
    .min(min, `${name} must be ${min} or more.`)
    .max(max, `${name} must be ${max} or less.`)
    .nullable();

export const unitSchema = z.object({
  label: z.string().trim().min(1, "Enter a label.").max(50, "Use at most 50 characters."),
  building_id: z.string(),
  floor: optionalInteger(-5, 300, "Floor"),
  bedrooms: optionalInteger(0, 50, "Bedrooms"),
  status: z.enum(UNIT_STATUSES),
});

export type UnitFormValues = z.infer<typeof unitSchema>;

export const UNIT_FIELDS = ["label", "building_id", "floor", "bedrooms", "status"] as const;

export const EMPTY_UNIT: UnitFormValues = {
  label: "",
  building_id: "",
  floor: null,
  bedrooms: null,
  status: "vacant",
};

export function unitFormValues(unit: Unit): UnitFormValues {
  return {
    label: unit.label,
    building_id: unit.building_id ?? "",
    floor: unit.floor,
    bedrooms: unit.bedrooms,
    status: unit.status,
  };
}

export function toUnitInput(values: UnitFormValues): UnitInput {
  return { ...values, building_id: values.building_id || null };
}

export function toUnitChanges(changes: Partial<UnitFormValues>): Partial<UnitInput> {
  const { building_id: buildingId, ...rest } = changes;
  return buildingId === undefined ? rest : { ...rest, building_id: buildingId || null };
}
