import { expect, test } from "./fixtures";
import {
  acceptAsNewUser,
  createProperty,
  inviteFromTeamPage,
  linkSentTo,
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
  uniqueEmail,
} from "./support";

test("a tenant reports an issue for their home and the owner sees it", async ({
  page,
  browser,
}) => {
  await ownerWithOrganization(page, "Riverside Estates");
  await propertyWithUnits(page, "Riverside Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Tom Tenant");

  await tenant
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Maintenance" })
    .click();
  await expect(tenant.getByText("You haven't reported any issues yet.")).toBeVisible();
  await tenant.getByRole("link", { name: "Report an issue" }).click();
  await expect(tenant.getByText("Reporting for Riverside Court · Unit A1")).toBeVisible();

  await tenant.getByRole("button", { name: "Submit report" }).click();
  await expect(tenant.getByText("Use at least 3 characters.")).toBeVisible();

  await tenant.getByLabel("Title").fill("Leaking kitchen pipe");
  await tenant.getByLabel("Category").selectOption("plumbing");
  await tenant.getByLabel("Priority").selectOption("high");
  await tenant
    .getByLabel("What's wrong?")
    .fill("Water drips under the sink.\nIt gets worse at night.");
  await tenant.getByLabel("Access notes (optional)").fill("Weekdays after 5pm.");
  await tenant.getByRole("button", { name: "Submit report" }).click();

  await expect(tenant).toHaveURL(/\/maintenance\/[0-9a-f-]{36}$/);
  await expect(
    tenant.getByRole("heading", { level: 1, name: "Leaking kitchen pipe" }),
  ).toBeVisible();
  await expect(tenant.getByText("Submitted")).toBeVisible();
  await expect(tenant.getByText("Riverside Court · Unit A1")).toBeVisible();
  await expect(tenant.getByText("It gets worse at night.", { exact: false })).toBeVisible();
  await tenant.context().close();

  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Maintenance" })
    .click();
  const item = page.getByRole("listitem").filter({ hasText: "Leaking kitchen pipe" });
  await expect(item).toContainText("reported by Tom Tenant");
  await expect(item).toContainText("High");
  await expect(item).toContainText("Submitted");
});

test("an owner reports a common-area issue for a property", async ({ page }) => {
  await ownerWithOrganization(page, "Common Estates");
  await createProperty(page, "Hilltop House");
  await page.goto("/maintenance/new");

  await page.getByRole("button", { name: "Submit report" }).click();
  await expect(page.getByText("Choose a property.")).toBeVisible();

  await page.getByLabel("Property", { exact: true }).selectOption({ label: "Hilltop House" });
  await expect(page.getByLabel("Unit", { exact: true })).toHaveValue("");
  await page.getByLabel("Title").fill("Broken gate lock");
  await page.getByLabel("Category").selectOption("security");
  await page.getByLabel("What's wrong?").fill("The main gate no longer locks.");
  await page.getByRole("button", { name: "Submit report" }).click();

  await expect(page.getByRole("heading", { level: 1, name: "Broken gate lock" })).toBeVisible();
  await expect(page.getByText("Hilltop House · Common area")).toBeVisible();
});

test("a tenant without a unit is told why they cannot report yet", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Waiting Estates");
  const email = uniqueEmail();
  await inviteFromTeamPage(page, email, "tenant");

  const context = await browser.newContext();
  const tenant = await context.newPage();
  await acceptAsNewUser(tenant, await linkSentTo(email, "/accept-invite"), "Una Unplaced");
  await tenant.goto("/maintenance/new");
  await expect(
    tenant.getByText("You haven't been placed in a unit yet", { exact: false }),
  ).toBeVisible();
  await expect(tenant.getByRole("button", { name: "Submit report" })).toHaveCount(0);
  await context.close();
});
