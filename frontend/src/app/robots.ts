import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/** Public pages may be indexed; signed-in pages, one-time links and the API may not. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/api/",
        "/dashboard",
        "/maintenance",
        "/work-orders",
        "/properties",
        "/tenants",
        "/contractors",
        "/settings",
        "/notifications",
        "/organizations",
        "/accept-invite",
        "/reset-password",
        "/verify-email",
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
