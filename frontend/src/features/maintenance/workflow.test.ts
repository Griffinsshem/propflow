import { describe, expect, it } from "vitest";

import { actionFor, orderedMoves, reasonProblem } from "./workflow";

describe("actionFor", () => {
  it("asks for a reason exactly where the API requires one", () => {
    expect(actionFor("in_progress", "waiting").reasonLabel).not.toBeNull();
    expect(actionFor("resolved", "in_progress").reasonLabel).not.toBeNull();
    expect(actionFor("submitted", "closed").reasonLabel).not.toBeNull();
    expect(actionFor("triaged", "closed").reasonLabel).not.toBeNull();
    expect(actionFor("submitted", "triaged").reasonLabel).toBeNull();
    expect(actionFor("resolved", "closed").reasonLabel).toBeNull();
  });

  it("still offers moves it has no wording for", () => {
    expect(actionFor("waiting", "resolved")).toEqual({
      label: "Move to Resolved",
      reasonLabel: null,
    });
  });
});

describe("orderedMoves", () => {
  it("follows the workflow and puts closing last", () => {
    expect(orderedMoves(["closed", "triaged"])).toEqual(["triaged", "closed"]);
    expect(orderedMoves(["resolved", "waiting"])).toEqual(["waiting", "resolved"]);
  });
});

describe("reasonProblem", () => {
  it("requires a reason within the API's limits", () => {
    expect(reasonProblem("")).toBe("Give a reason.");
    expect(reasonProblem("x".repeat(1001))).toMatch(/1000/);
    expect(reasonProblem("Waiting for a part")).toBeNull();
  });
});
