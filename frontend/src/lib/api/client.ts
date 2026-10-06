import { ApiError } from "./errors";

// Production uses the __Host- prefixed name; development and tests use the plain one.
const CSRF_COOKIES = ["__Host-propflow_csrf", "propflow_csrf"];
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function readCsrfToken(
  cookies = typeof document === "undefined" ? "" : document.cookie,
) {
  for (const part of cookies.split(";")) {
    const [name, ...value] = part.trim().split("=");
    if (CSRF_COOKIES.includes(name)) return decodeURIComponent(value.join("="));
  }
  return null;
}

type RequestOptions = { method?: string; body?: unknown; signal?: AbortSignal };

/** Calls the API through this origin's proxy. Throws ApiError for every failure. */
export async function apiRequest<T>(
  path: string,
  { method = "GET", body, signal }: RequestOptions = {},
): Promise<T> {
  const headers = new Headers({ Accept: "application/json" });
  if (body !== undefined) headers.set("Content-Type", "application/json");
  if (UNSAFE_METHODS.has(method)) {
    const csrf = readCsrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw ApiError.network();
  }

  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw ApiError.fromResponse(
      response.status,
      payload,
      response.headers.get("x-request-id"),
    );
  }
  return payload as T;
}
