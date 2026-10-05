/**
 * Pure rules for the API proxy (no I/O, unit-tested): what is forwarded, and what never is.
 */

export const PROXY_SECRET_HEADER = "x-proxy-secret";

// Only these request headers reach the API; anything else the browser sends is dropped,
// including attempts to supply x-proxy-secret or x-forwarded-for.
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "content-type",
  "cookie",
  "origin",
  "user-agent",
  "x-csrf-token",
  "x-request-id",
] as const;

const FORWARDED_RESPONSE_HEADERS = [
  "content-type",
  "cache-control",
  "retry-after",
  "x-request-id",
  "x-ratelimit-limit",
  "x-ratelimit-remaining",
  "x-ratelimit-reset",
] as const;

/** The API URL for a proxied path, or null for anything that could escape /api/v1. */
export function upstreamUrl(origin: string, segments: string[], search: string): URL | null {
  const unsafe = (segment: string) =>
    segment === "" || segment === "." || segment === ".." || /[/\\]/.test(segment);
  if (segments.length === 0 || segments.some(unsafe)) {
    return null;
  }
  const path = segments.map(encodeURIComponent).join("/");
  return new URL(`/api/v1/${path}${search}`, origin);
}

/** The client IP as reported by the hosting platform (on Vercel, set by the platform). */
export function clientIpFrom(incoming: Headers): string | undefined {
  return incoming.get("x-forwarded-for")?.split(",")[0]?.trim() || undefined;
}

export function upstreamRequestHeaders(
  incoming: Headers,
  options: { secret?: string; clientIp?: string },
): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = incoming.get(name);
    if (value !== null) headers.set(name, value);
  }
  if (options.secret) headers.set(PROXY_SECRET_HEADER, options.secret);
  // Exactly one value: the hosting edge in front of the API appends its own hop after it.
  if (options.clientIp) headers.set("x-forwarded-for", options.clientIp);
  return headers;
}

export function downstreamHeaders(upstream: Headers): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.get(name);
    if (value !== null) headers.set(name, value);
  }
  for (const cookie of upstream.getSetCookie()) {
    headers.append("set-cookie", cookie);
  }
  if (!headers.has("cache-control")) headers.set("cache-control", "no-store");
  return headers;
}
