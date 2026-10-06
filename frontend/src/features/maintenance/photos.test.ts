import { describe, expect, it } from "vitest";

import { photoProblem } from "./photos";

describe("photoProblem", () => {
  it("accepts JPEG, PNG and WebP within the size limit", () => {
    for (const type of ["image/jpeg", "image/png", "image/webp"]) {
      expect(photoProblem({ type, size: 1000 })).toBeNull();
    }
  });

  it("refuses other types, empty files and files over 10 MB", () => {
    expect(photoProblem({ type: "text/plain", size: 10 })).toMatch(/Only JPEG/);
    expect(photoProblem({ type: "image/gif", size: 10 })).toMatch(/Only JPEG/);
    expect(photoProblem({ type: "image/png", size: 0 })).toMatch(/empty/);
    expect(photoProblem({ type: "image/png", size: 10 * 1024 * 1024 + 1 })).toMatch(/10 MB/);
  });
});
