// @vitest-environment node
import { describe, expect, it } from "vitest";

import { downstreamHeaders, upstreamRequestHeaders, upstreamUrl } from "./upstream";

describe("upstreamUrl", () => {
  it("builds API URLs and keeps the query string", () => {
    expect(upstreamUrl("http://api:5000", ["maintenance", "abc"], "?limit=5")?.toString()).toBe(
      "http://api:5000/api/v1/maintenance/abc?limit=5",
    );
  });

  it.each([
    { segments: [] },
    { segments: [""] },
    { segments: [".."] },
    { segments: ["auth", "..", "..", "health"] },
    { segments: ["a/b"] },
    { segments: ["a\\b"] },
  ])("refuses paths that could escape /api/v1: $segments", ({ segments }) => {
    expect(upstreamUrl("http://api:5000", segments, "")).toBeNull();
  });
});

describe("upstreamRequestHeaders", () => {
  it("forwards an allowlist, adds the secret and drops spoofed values", () => {
    const incoming = new Headers({
      cookie: "propflow_session=s",
      "x-csrf-token": "t",
      "x-proxy-secret": "spoofed",
      "x-forwarded-for": "198.51.100.66",
      authorization: "Bearer stolen",
    });
    const headers = upstreamRequestHeaders(incoming, {
      secret: "s".repeat(40),
      clientIp: "203.0.113.7",
    });
    expect(headers.get("cookie")).toBe("propflow_session=s");
    expect(headers.get("x-csrf-token")).toBe("t");
    expect(headers.get("x-proxy-secret")).toBe("s".repeat(40));
    expect(headers.get("x-forwarded-for")).toBe("203.0.113.7");
    expect(headers.get("authorization")).toBeNull();
  });

  it("sends no secret header when none is configured", () => {
    const headers = upstreamRequestHeaders(new Headers({ "x-proxy-secret": "spoofed" }), {});
    expect(headers.get("x-proxy-secret")).toBeNull();
  });
});

describe("downstreamHeaders", () => {
  it("keeps every Set-Cookie, drops server details and defaults to no-store", () => {
    const upstream = new Headers({ "content-type": "application/json", server: "gunicorn" });
    upstream.append("set-cookie", "a=1; Path=/");
    upstream.append("set-cookie", "b=2; Path=/");
    const headers = downstreamHeaders(upstream);
    expect(headers.getSetCookie()).toEqual(["a=1; Path=/", "b=2; Path=/"]);
    expect(headers.get("server")).toBeNull();
    expect(headers.get("cache-control")).toBe("no-store");
  });
});
