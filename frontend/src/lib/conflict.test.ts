import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/errors";

import {
  changedFields,
  detectStaleConflict,
  diffValues,
  mergeKeepingMine,
} from "./conflict";

const original = { name: "Court", city: "Nairobi", region: "" };

describe("diffValues", () => {
  it("returns only the fields that changed", () => {
    expect(diffValues({ ...original, name: "Court II" }, original)).toEqual({
      name: "Court II",
    });
    expect(diffValues(original, original)).toEqual({});
  });
});

describe("mergeKeepingMine", () => {
  it("keeps my edits and takes their values for everything I did not touch", () => {
    const mine = { ...original, name: "Mine" };
    const latest = { ...original, city: "Mombasa" };
    expect(mergeKeepingMine(mine, original, latest)).toEqual({
      name: "Mine",
      city: "Mombasa",
      region: "",
    });
  });
});

describe("changedFields", () => {
  it("lists their changes with labels, showing empty values explicitly", () => {
    const latest = { ...original, city: "Mombasa", region: "" };
    expect(
      changedFields(original, latest, { name: "Name", city: "City" }),
    ).toEqual([{ field: "city", label: "City", value: "Mombasa" }]);
    expect(
      changedFields(latest, original, { city: "City", region: "Region" })[0],
    ).toMatchObject({
      label: "City",
      value: "Nairobi",
    });
  });
});

describe("detectStaleConflict", () => {
  const conflict = new ApiError(409, "CONFLICT", "Changed by someone else.");

  it("returns the latest version when someone else saved first", async () => {
    const latest = { version: 3 };
    await expect(
      detectStaleConflict(conflict, 2, async () => latest),
    ).resolves.toBe(latest);
  });

  it("is not a stale conflict when the version did not move (e.g. a duplicate)", async () => {
    await expect(
      detectStaleConflict(conflict, 2, async () => ({ version: 2 })),
    ).resolves.toBeNull();
  });

  it("ignores other errors without fetching", async () => {
    const fetchLatest = vi.fn();
    await expect(
      detectStaleConflict(new Error("x"), 2, fetchLatest),
    ).resolves.toBeNull();
    expect(fetchLatest).not.toHaveBeenCalled();
  });
});
