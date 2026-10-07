import { describe, expect, it } from "vitest";

import {
  contractorSchema,
  EMPTY_CONTRACTOR,
  toContractorChanges,
  toContractorInput,
} from "./schemas";

const valid = {
  ...EMPTY_CONTRACTOR,
  business_name: "Fixit Plumbing",
  specialty: "plumbing" as const,
};

describe("contractorSchema", () => {
  it("accepts optional fields left blank", () => {
    expect(contractorSchema.safeParse(valid).success).toBe(true);
  });

  it("requires international phone numbers, as the API does", () => {
    expect(contractorSchema.safeParse({ ...valid, phone: "0712345678" }).success).toBe(false);
    expect(contractorSchema.safeParse({ ...valid, phone: "+254712345678" }).success).toBe(true);
  });

  it("validates email only when one is given", () => {
    expect(contractorSchema.safeParse({ ...valid, email: "not-an-email" }).success).toBe(false);
    expect(contractorSchema.safeParse({ ...valid, email: "fixit@example.com" }).success).toBe(true);
  });
});

describe("payloads", () => {
  it("send blanks as null and never send a status on create", () => {
    const input = toContractorInput(valid);
    expect(input).toMatchObject({ contact_name: null, phone: null, email: null });
    expect(input).not.toHaveProperty("status");
  });

  it("clear optional fields with null on update", () => {
    expect(toContractorChanges({ phone: "", business_name: "Fixit" })).toEqual({
      phone: null,
      business_name: "Fixit",
    });
  });
});
