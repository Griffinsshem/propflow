import { describe, expect, it } from "vitest";

import { navFor } from "./nav";

const labels = (role: Parameters<typeof navFor>[0]) => navFor(role).map((item) => item.label);

describe("navFor", () => {
  it("shows organization settings to owners and managers", () => {
    expect(labels("owner")).toEqual(["Dashboard", "Properties", "Tenants", "Team", "Organization"]);
    expect(labels("manager")).toEqual([
      "Dashboard",
      "Properties",
      "Tenants",
      "Team",
      "Organization",
    ]);
  });

  it("keeps tenants and contractors to their own sections", () => {
    expect(labels("tenant")).toEqual(["Dashboard"]);
    expect(labels("contractor")).toEqual(["Dashboard"]);
  });

  it("shows only the dashboard without an active organization", () => {
    expect(labels(null)).toEqual(["Dashboard"]);
  });
});
