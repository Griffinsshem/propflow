import { describe, expect, it } from "vitest";

import type { Comment, HistoryEntry } from "@/lib/api/maintenance";

import { describeStatusChange, mergeActivity } from "./activity";

const person = (full_name: string) => ({ membership_id: full_name, full_name });

const reported: HistoryEntry = {
  from_status: null,
  to_status: "submitted",
  reason: null,
  changed_by: person("Tom Tenant"),
  created_at: "2026-10-01T09:00:00Z",
};
const triaged: HistoryEntry = {
  from_status: "submitted",
  to_status: "triaged",
  reason: null,
  changed_by: person("Mary Manager"),
  created_at: "2026-10-01T11:00:00Z",
};
const comment = (id: string, created_at: string): Comment => ({
  id,
  body: `comment ${id}`,
  author: person("Olivia Owner"),
  created_at,
});

describe("mergeActivity", () => {
  it("orders status changes and comments by time, oldest first", () => {
    const merged = mergeActivity([triaged, reported], [comment("c1", "2026-10-01T10:00:00Z")]);
    expect(merged.map((item) => item.key)).toEqual(["status-1", "comment-c1", "status-0"]);
  });

  it("puts a status change before a comment made at the same moment", () => {
    const merged = mergeActivity([triaged], [comment("c1", triaged.created_at)]);
    expect(merged.map((item) => item.kind)).toEqual(["status", "comment"]);
  });

  it("keeps the API's order for entries with identical times", () => {
    const merged = mergeActivity(
      [],
      [comment("a", "2026-10-01T10:00:00Z"), comment("b", "2026-10-01T10:00:00Z")],
    );
    expect(merged.map((item) => item.key)).toEqual(["comment-a", "comment-b"]);
  });
});

describe("describeStatusChange", () => {
  it("describes the original report and later moves", () => {
    expect(describeStatusChange(reported)).toBe("Tom Tenant reported this issue");
    expect(describeStatusChange(triaged)).toBe("Mary Manager moved this from Submitted to Triaged");
  });
});
