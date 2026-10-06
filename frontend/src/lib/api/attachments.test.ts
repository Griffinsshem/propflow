import { describe, expect, it, vi } from "vitest";

import { uploadToStorage } from "./attachments";

const upload = {
  method: "PUT",
  url: "https://storage.example/key?signature=abc",
  headers: { "Content-Type": "image/png" },
  expires_in: 300,
};

describe("uploadToStorage", () => {
  it("sends exactly the signed method and headers, without cookies", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new Blob(["png"], { type: "image/png" });
    await uploadToStorage(upload, file);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(upload.url);
    expect(init).toMatchObject({ method: "PUT", headers: upload.headers, credentials: "omit" });
    expect(init.body).toBe(file);
  });

  it("reports storage refusals and network failures as errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 403 })),
    );
    await expect(uploadToStorage(upload, new Blob(["x"]))).rejects.toThrow("could not be uploaded");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("offline");
      }),
    );
    await expect(uploadToStorage(upload, new Blob(["x"]))).rejects.toThrow("Check your connection");
  });
});
