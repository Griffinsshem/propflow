import { expect, test } from "./fixtures";
import {
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
  reportAsTenant,
} from "./support";

test("a tenant is notified when their request moves, opens it, and catches up", async ({
  page,
  browser,
}) => {
  await ownerWithOrganization(page, "Notify Estates");
  await propertyWithUnits(page, "Notify Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Nia Tenant");
  await reportAsTenant(tenant, "Burst pipe");
  await page.goto(tenant.url());
  await page
    .getByRole("group", { name: "Status actions" })
    .getByRole("button", { name: "Triage" })
    .click();
  await expect(page.getByText("Triaged", { exact: true })).toBeVisible();

  await tenant.goto("/dashboard");
  const bell = tenant.getByRole("link", { name: /^Notifications, \d+ unread$/ });
  await expect(bell).toBeVisible();
  await bell.click();
  await expect(tenant).toHaveURL(/\/notifications$/);

  const latest = tenant.getByRole("list", { name: "Notifications" }).getByRole("listitem").first();
  await expect(latest).toContainText("Maintenance request updated");
  await expect(latest).toContainText("Burst pipe is now triaged.");
  await latest.getByRole("link").click();
  await expect(tenant).toHaveURL(/\/maintenance\/[0-9a-f-]{36}$/);
  await expect(tenant.getByRole("heading", { level: 1, name: "Burst pipe" })).toBeVisible();

  await tenant.goto("/notifications");
  await expect(tenant.getByRole("heading", { level: 1, name: "Notifications" })).toBeVisible();
  await tenant.getByRole("button", { name: "Mark all as read" }).click();
  await expect(tenant.getByRole("link", { name: "Notifications", exact: true })).toBeVisible();
  await tenant.getByLabel("Unread only").check();
  await expect(tenant).toHaveURL(/\/notifications\?unread=1$/);
  await expect(tenant.getByText("You're all caught up.")).toBeVisible();
  await tenant.context().close();
});
