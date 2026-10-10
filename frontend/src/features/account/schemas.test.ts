import { describe, expect, it } from "vitest";

import { emailSchema, newPasswordSchema } from "./schemas";

describe("emailSchema", () => {
  it("requires a valid address", () => {
    expect(emailSchema.safeParse({ email: "" }).success).toBe(false);
    expect(emailSchema.safeParse({ email: "not-an-email" }).success).toBe(false);
    expect(emailSchema.safeParse({ email: " rita@example.com " }).success).toBe(true);
  });
});

describe("newPasswordSchema", () => {
  const good = "a brand new passphrase";

  it("enforces the API's length rules", () => {
    expect(newPasswordSchema.safeParse({ password: "short", confirm: "short" }).success).toBe(
      false,
    );
    const tooLong = "x".repeat(129);
    expect(newPasswordSchema.safeParse({ password: tooLong, confirm: tooLong }).success).toBe(
      false,
    );
    expect(newPasswordSchema.safeParse({ password: good, confirm: good }).success).toBe(true);
  });

  it("requires both entries to match, reporting it on the confirmation", () => {
    const result = newPasswordSchema.safeParse({ password: good, confirm: `${good}!` });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0]?.path).toEqual(["confirm"]);
  });
});
