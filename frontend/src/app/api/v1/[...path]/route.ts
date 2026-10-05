import type { NextRequest } from "next/server";

import { serverEnv } from "@/lib/server/env";
import {
  clientIpFrom,
  downstreamHeaders,
  upstreamRequestHeaders,
  upstreamUrl,
} from "@/lib/server/upstream";

// The browser only ever talks to this origin; this handler is the single path to the API.
export const dynamic = "force-dynamic";

const TIMEOUT_MS = 30_000;

type Context = { params: Promise<{ path: string[] }> };

function errorEnvelope(status: number, code: string, message: string): Response {
  return Response.json(
    { error: { code, message, request_id: null } },
    { status, headers: { "cache-control": "no-store" } },
  );
}

async function forward(request: NextRequest, { params }: Context): Promise<Response> {
  const { path } = await params;
  const env = serverEnv();
  const target = upstreamUrl(env.API_ORIGIN, path, request.nextUrl.search);
  if (target === null) {
    return errorEnvelope(404, "RESOURCE_NOT_FOUND", "The requested resource was not found.");
  }
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers: upstreamRequestHeaders(request.headers, {
        secret: env.PROXY_SHARED_SECRET,
        clientIp: clientIpFrom(request.headers),
      }),
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: downstreamHeaders(upstream.headers),
    });
  } catch {
    return errorEnvelope(
      502,
      "UPSTREAM_UNAVAILABLE",
      "PropFlow is temporarily unavailable. Please try again.",
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
