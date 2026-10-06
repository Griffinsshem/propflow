import { NextResponse, type NextRequest } from "next/server";

/**
 * Per-request Content Security Policy with a script nonce (ADR 0016).
 * Scripts: only nonce-bearing scripts (and what they load) may run, which blocks injected JS.
 * Styles: inline styles are allowed; Next's route announcer needs them, and style injection
 * is a far smaller risk than script injection.
 */
/** STORAGE_ORIGIN (server-only): the object storage origin browsers upload to and load
 * photos from. Normalized to a bare origin; anything unparsable is ignored, not trusted. */
function storageOrigin(): string {
  const configured = process.env.STORAGE_ORIGIN;
  if (!configured) return "";
  try {
    return ` ${new URL(configured).origin}`;
  } catch {
    return "";
  }
}

export function proxy(request: NextRequest) {
  const nonce = btoa(crypto.randomUUID());
  const isDev = process.env.NODE_ENV === "development";
  const storage = storageOrigin();
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' blob: data:${storage}`,
    "font-src 'self'",
    `connect-src 'self'${storage}${isDev ? " ws:" : ""}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    ...(isDev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("content-security-policy", csp);
  return response;
}

export const config = {
  matcher: [
    {
      source: "/((?!api|_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
