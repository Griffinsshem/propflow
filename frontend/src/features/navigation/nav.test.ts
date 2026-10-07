import { describe, expect, it } from "vitest";

import { navFor } from "./nav";

const labels = (role: Parameters<typeof navFor>[0]) => navFor(role).map((item) => item.label);
const WORKSPACE = [
  "Dashboard",
  "Maintenance",
  "Work orders",
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

  it("gives contractors their dashboard and their jobs", () => {
    expect(labels("contractor")).toEqual(["Dashboard", "Work orders"]);
  });

  it("shows only the dashboard without an active organization", () => {
    expect(labels(null)).toEqual(["Dashboard"]);
  });
});
