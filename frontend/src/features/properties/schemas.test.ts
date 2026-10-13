import { describe, expect, it } from "vitest";

import {
  EMPTY_PROPERTY,
  propertySchema,
  toPropertyChanges,
  toUnitChanges,
  unitSchema,
} from "./schemas";

describe("propertySchema", () => {
  it("normalizes the country code and allows blank optional fields", () => {
    const parsed = propertySchema.parse({
      ...EMPTY_PROPERTY,
      name: " Court ",
      address_line: "1 Road",
      city: "Nairobi",
      country_code: "ke",
    });
    expect(parsed).toMatchObject({
      name: "Court",
      country_code: "KE",
      region: "",
    });
  });

  it("rejects malformed country codes", () => {
    const result = propertySchema.safeParse({
      ...EMPTY_PROPERTY,
      name: "Court",
      address_line: "1 Road",
      city: "Nairobi",
      country_code: "KEN",
    });
    expect(result.success).toBe(false);
  });
});

describe("unitSchema", () => {
  it("accepts missing numbers and enforces the API's ranges", () => {
    const base = { label: "A1", building_id: "", status: "vacant" as const };
    expect(unitSchema.safeParse({ ...base, floor: null, bedrooms: null }).success).toBe(true);
    expect(unitSchema.safeParse({ ...base, floor: 301, bedrooms: null }).success).toBe(false);
    expect(unitSchema.safeParse({ ...base, floor: 1, bedrooms: 2.5 }).success).toBe(false);
  });
});

describe("change payloads", () => {
  it("turn blank optional text and 'no building' into null", () => {
    expect(toPropertyChanges({ region: "", city: "Mombasa" })).toEqual({
      region: null,
      city: "Mombasa",
    });
    expect(toUnitChanges({ building_id: "", label: "A2" })).toEqual({
      building_id: null,
      label: "A2",
    });
    expect(toUnitChanges({ label: "A2" })).toEqual({ label: "A2" });
  });
});
