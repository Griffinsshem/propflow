// Wakes the API (ADR 0019): /health needs no proxy secret and changes nothing.
const API_ORIGIN = process.env.API_ORIGIN || "http://127.0.0.1:5000";

export async function POST(): Promise<Response> {
  try {
    await fetch(`${API_ORIGIN}/health`, { cache: "no-store", signal: AbortSignal.timeout(55_000) });
  } catch {
    // Best effort: a failed wake-up only means the next request waits a little longer.
  }
  return new Response(null, { status: 204 });
}
