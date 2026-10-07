import { describe, expect, it } from "vitest";

import { assignSchema, todayIso, toWorkOrderInput } from "./schemas";
import { orderedWorkOrderMoves, workOrderActionFor } from "./workflow";

const valid = { contractor_id: "c1", priority: "normal" as const, due_date: "", description: "" };

describe("workOrderActionFor", () => {
  it("asks for a reason exactly where the API requires one", () => {
    expect(workOrderActionFor("assigned", "declined").reasonLabel).not.toBeNull();
    for (const from of ["assigned", "accepted", "in_progress"] as const) {
      expect(workOrderActionFor(from, "cancelled").reasonLabel).not.toBeNull();
    }
    expect(workOrderActionFor("assigned", "accepted").reasonLabel).toBeNull();
    expect(workOrderActionFor("in_progress", "completed").reasonLabel).toBeNull();
  });
});

describe("orderedWorkOrderMoves", () => {
  it("puts progress first and declining or cancelling last", () => {
    expect(orderedWorkOrderMoves(["cancelled", "declined", "accepted"])).toEqual([
      "accepted",
      "declined",
      "cancelled",
    ]);
  });
});

describe("assignSchema", () => {
  it("requires a contractor and refuses due dates in the past", () => {
    expect(assignSchema.safeParse(valid).success).toBe(true);
    expect(assignSchema.safeParse({ ...valid, contractor_id: "" }).success).toBe(false);
    expect(assignSchema.safeParse({ ...valid, due_date: "2000-01-01" }).success).toBe(false);
    expect(assignSchema.safeParse({ ...valid, due_date: todayIso() }).success).toBe(true);
  });

  it("sends blanks as null", () => {
    expect(toWorkOrderInput("r1", valid)).toEqual({
      request_id: "r1",
      contractor_id: "c1",
      priority: "normal",
      description: null,
      due_date: null,
    });
  });
});
