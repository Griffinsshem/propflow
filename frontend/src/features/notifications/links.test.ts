import { describe, expect, it } from "vitest";

import { linkFor } from "./links";

describe("linkFor", () => {
  it("links requests and work orders to their pages", () => {
    expect(linkFor("maintenance_request", "r1")).toBe("/maintenance/r1");
    expect(linkFor("work_order", "w1")).toBe("/work-orders/w1");
  });

  it("gives no link for types it does not know", () => {
    expect(linkFor("invoice", "x")).toBeNull();
  });
});
