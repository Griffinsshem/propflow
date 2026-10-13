import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "./client";
import { ApiError } from "./errors";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  document.cookie = "propflow_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

describe("apiRequest", () => {
  it("echoes the CSRF cookie on unsafe methods only", async () => {
    document.cookie = "propflow_csrf=token-123; path=/";
    const fetchMock = vi.fn(async () => jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/auth/logout", { method: "POST" });
    await apiRequest("/auth/me");

    const calls = fetchMock.mock.calls as unknown as [string, RequestInit][];
    expect(new Headers(calls[0][1].headers).get("X-CSRF-Token")).toBe("token-123");
    expect(new Headers(calls[1][1].headers).get("X-CSRF-Token")).toBeNull();
    expect(calls[0][0]).toBe("/api/v1/auth/logout");
  });

  it("turns the error envelope into an ApiError with field messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(422, {
          error: {
            code: "VALIDATION_ERROR",
            message: "The request contains invalid data.",
            request_id: "req-1",
            details: { json: { email: ["Not a valid email address."] } },
          },
        }),
      ),
    );
    const error = await apiRequest("/auth/register", {
      method: "POST",
      body: {},
    }).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      requestId: "req-1",
      fieldErrors: { email: ["Not a valid email address."] },
    });
  });

  it("reports network failures distinctly", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    await expect(apiRequest("/auth/me")).rejects.toMatchObject({
      status: 0,
      code: "NETWORK_ERROR",
    });
  });

  it("returns nothing for 204 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 204 })),
    );
    await expect(apiRequest("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });
});
