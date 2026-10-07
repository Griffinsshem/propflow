import { describe, expect, it } from "vitest";

import { navFor } from "./nav";

const labels = (role: Parameters<typeof navFor>[0]) => navFor(role).map((item) => item.label);
const WORKSPACE = [
  "Dashboard",
  "Maintenance",
  "Properties",
  "Tenants",
  "Contractors",
  "Team",
  "Organization",
];

describe("navFor", () => {
  it("gives owners and managers the full workspace", () => {
    expect(labels("owner")).toEqual(WORKSPACE);
    expect(labels("manager")).toEqual(WORKSPACE);
  });

  it("gives tenants their dashboard and their requests", () => {
    expect(labels("tenant")).toEqual(["Dashboard", "Maintenance"]);
  });

  it("keeps contractors to their dashboard", () => {
    expect(labels("contractor")).toEqual(["Dashboard"]);
  });

  it("shows only the dashboard without an active organization", () => {
    expect(labels(null)).toEqual(["Dashboard"]);
  });
});
