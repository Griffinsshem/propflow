import { describe, expect, it } from "vitest";

import { EMPTY_REPORT, hasControlCharacters, reportSchema, toMaintenanceInput } from "./schemas";

const valid = {
  ...EMPTY_REPORT,
  title: "Leaking pipe",
  description: "Water under the sink.\nWorse at night.",
};

describe("hasControlCharacters", () => {
  it("allows newlines and tabs but refuses other control characters", () => {
    expect(hasControlCharacters("line one\nline two\tindented")).toBe(false);
    expect(hasControlCharacters(`bell${String.fromCharCode(7)}`)).toBe(true);
    expect(hasControlCharacters(`delete${String.fromCharCode(127)}`)).toBe(true);
  });
});

describe("reportSchema", () => {
  it("requires a property from staff but not from tenants", () => {
    expect(reportSchema(false).safeParse(valid).success).toBe(true);
    expect(reportSchema(true).safeParse(valid).success).toBe(false);
    expect(reportSchema(true).safeParse({ ...valid, property_id: "p1" }).success).toBe(true);
  });

  it("enforces the API's title length", () => {
    expect(reportSchema(false).safeParse({ ...valid, title: "ab" }).success).toBe(false);
  });
});

describe("toMaintenanceInput", () => {
  it("never sends a location for tenants", () => {
    const input = toMaintenanceInput({ ...valid, property_id: "p1", unit_id: "u1" }, false);
    expect(input).not.toHaveProperty("property_id");
    expect(input).not.toHaveProperty("unit_id");
    expect(input.access_notes).toBeNull();
  });

  it("sends staff locations, omitting the unit for common areas", () => {
    expect(toMaintenanceInput({ ...valid, property_id: "p1" }, true)).toMatchObject({
      property_id: "p1",
    });
    expect(toMaintenanceInput({ ...valid, property_id: "p1" }, true)).not.toHaveProperty("unit_id");
    expect(toMaintenanceInput({ ...valid, property_id: "p1", unit_id: "u1" }, true)).toMatchObject({
      unit_id: "u1",
    });
  });
});
