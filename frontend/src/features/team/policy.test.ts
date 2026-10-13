import { describe, expect, it } from "vitest";

import { invitableRoles } from "./policy";

describe("invitableRoles", () => {
  it("lets owners invite every role", () => {
    expect(invitableRoles("owner")).toEqual(["manager", "contractor", "tenant", "owner"]);
  });

  it("limits managers to tenants and contractors", () => {
    expect(invitableRoles("manager")).toEqual(["contractor", "tenant"]);
  });

  it("gives tenants and contractors nothing to invite", () => {
    expect(invitableRoles("tenant")).toEqual([]);
    expect(invitableRoles("contractor")).toEqual([]);
  });
});
