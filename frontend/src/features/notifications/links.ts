/**
 * Where a notification leads. Keys are the resource types the API uses
 * (backend/app/notifications/service.py); scripts/check_notification_links.py fails CI if a
 * type is missing. Types the interface doesn't know get no link, never a wrong one.
 */
const PAGES: Record<string, (id: string) => string> = {
  maintenance_request: (id) => `/maintenance/${encodeURIComponent(id)}`,
  work_order: (id) => `/work-orders/${encodeURIComponent(id)}`,
};

export function linkFor(resourceType: string, resourceId: string): string | null {
  const page = PAGES[resourceType];
  return page ? page(resourceId) : null;
}
