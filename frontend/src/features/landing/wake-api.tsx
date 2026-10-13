"use client";

import { useEffect } from "react";

/**
 * The free API sleeps after 15 idle minutes (ADR 0019). One beacon from the landing page wakes
 * it while the visitor reads, so the sign-in that follows is fast. Fire and forget.
 */
export function WakeApi() {
  useEffect(() => {
    navigator.sendBeacon?.("/api/wake");
  }, []);
  return null;
}
