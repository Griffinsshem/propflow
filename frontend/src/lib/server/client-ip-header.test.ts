import { describe, expect, it } from "vitest";

import { upstreamRequestHeaders } from "./upstream";

describe("the visitor's IP for the API (ADR 0020)", () => {
  it("is sent in the proxy's own header", () => {
    const headers = upstreamRequestHeaders(new Headers(), {
      secret: "s".repeat(48),
      clientIp: "203.0.113.9",
    });
    expect(headers.get("x-propflow-client-ip")).toBe("203.0.113.9");
  });

  it("can never be supplied by the browser", () => {
    const incoming = new Headers({ "x-propflow-client-ip": "6.6.6.6" });
    const headers = upstreamRequestHeaders(incoming, { secret: "s".repeat(48) });
    expect(headers.get("x-propflow-client-ip")).toBeNull();
  });
});
