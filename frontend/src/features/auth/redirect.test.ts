import { describe, expect, it } from "vitest";

import { safeNextPath } from "./redirect";

describe("safeNextPath", () => {
  it.each(["/dashboard", "/maintenance/123?tab=history"])("accepts local path %s", (path) => {
    expect(safeNextPath(path)).toBe(path);
  });

  it.each([undefined, "", "https://evil.example", "//evil.example", "/\\evil.example", "dashboard"])(
    "falls back for unsafe value %s",
    (value) => {
      expect(safeNextPath(value)).toBe("/dashboard");
    },
  );

  it("uses the first value when a parameter repeats", () => {
    expect(safeNextPath(["/a", "/b"])).toBe("/a");
  });
});
