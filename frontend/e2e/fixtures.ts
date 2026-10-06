/**
 * Every test acts as a distinct visitor, as real users would: a unique X-Forwarded-For per test.
 * The frontend proxy forwards it and the API (TRUSTED_PROXY_COUNT=1 in test runs) keys its per-IP
 * rate limits on it, so the suite never trips limits meant for one person. All limits stay on.
 * In production the hosting platform sets this header; the F6 deployment checks verify it.
 */
import { randomInt } from "node:crypto";

import { test as base } from "@playwright/test";

export { expect } from "@playwright/test";
export type { Page } from "@playwright/test";

export const test = base.extend({
  extraHTTPHeaders: async ({ extraHTTPHeaders }, provide) => {
    // 198.18.0.0/15 is reserved for network testing: never a real visitor's address.
    const address = `198.${18 + randomInt(2)}.${randomInt(256)}.${randomInt(1, 255)}`;
    await provide({ ...extraHTTPHeaders, "x-forwarded-for": address });
  },
});
