/** Only same-site paths are accepted as a post-login destination (prevents open redirects). */
export function safeNextPath(value: string | string[] | undefined, fallback = "/dashboard") {
  const candidate = Array.isArray(value) ? value[0] : value;
  if (!candidate || !candidate.startsWith("/") || /^\/[/\\]/.test(candidate)) return fallback;
  return candidate;
}
