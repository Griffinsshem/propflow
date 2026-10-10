"use client";

import { useSyncExternalStore } from "react";

// Emailed links carry their token after "#", which browsers never send to any server.
const TOKEN = /(?:^#|&)token=([A-Za-z0-9_.-]+)/;

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

/** undefined while rendering on the server; null when the link has no token. */
export function useHashToken(): string | null | undefined {
  const hash = useSyncExternalStore(
    subscribe,
    () => window.location.hash,
    () => null,
  );
  return hash === null ? undefined : (TOKEN.exec(hash)?.[1] ?? null);
}
