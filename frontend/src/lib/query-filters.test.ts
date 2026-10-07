import { describe, expect, it } from "vitest";

import { pick, uuidOrEmpty } from "./query-filters";

describe("pick", () => {
  it("keeps allowed values and drops anything else from the address", () => {
    expect(pick("submitted", ["submitted", "closed"] as const)).toBe("submitted");
    expect(pick("<script>", ["submitted", "closed"] as const)).toBe("");
    expect(pick(null, ["submitted"] as const)).toBe("");
  });
});

describe("uuidOrEmpty", () => {
  it("accepts only identifiers", () => {
    expect(uuidOrEmpty("3f2b8c1e-1d2a-4c3b-9e8f-0a1b2c3d4e5f")).toBe(
      "3f2b8c1e-1d2a-4c3b-9e8f-0a1b2c3d4e5f",
    );
    expect(uuidOrEmpty("../../etc")).toBe("");
  });
});
