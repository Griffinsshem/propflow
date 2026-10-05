import "server-only";

import { z } from "zod";

// Server-only settings: never prefixed NEXT_PUBLIC_, so they never reach the browser bundle.
const schema = z.object({
  API_ORIGIN: z.string().url().default("http://127.0.0.1:5000"),
  // Optional locally; when set, the backend rejects any /api request that lacks it.
  PROXY_SHARED_SECRET: z.string().min(32).optional(),
});

export type ServerEnv = z.infer<typeof schema>;

let cached: ServerEnv | undefined;

export function serverEnv(): ServerEnv {
  cached ??= schema.parse({
    API_ORIGIN: process.env.API_ORIGIN || undefined,
    PROXY_SHARED_SECRET: process.env.PROXY_SHARED_SECRET || undefined,
  });
  return cached;
}
