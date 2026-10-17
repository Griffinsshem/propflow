/** The site's public address: Vercel's production address, else local development. */
const production = process.env.VERCEL_PROJECT_PRODUCTION_URL;
export const SITE_URL = production ? `https://${production}` : "http://localhost:3000";
