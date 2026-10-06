import { expect, test, type Page } from "./fixtures";

import {
  acceptAsNewUser,
  createProperty,
  linkSentTo,
  ownerWithOrganization,
  uniqueEmail,
} from "./support";

async function propertyWithUnits(page: Page, name: string, labels: string[]): Promise<string> {
  const url = await createProperty(page, name);
  for (const label of labels) {
    await page.getByLabel("Unit label").fill(label);
    await page.getByRole("button", { name: "Add unit" }).click();
    await expect(page.getByText(`Unit ${label} added.`)).toBeVisible();
  }
  return url;
}

async function openUnit(page: Page, label: string): Promise<void> {
  await page.getByRole("link", { name: label, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: `Unit ${label}` })).toBeVisible();
}

async function inviteTenantHere(page: Page, email: string): Promise<void> {
  await page.getByLabel("Tenant email").fill(email);
  await page.getByRole("button", { name: "Invite tenant" }).click();
  await expect(page.getByText(`Invitation sent to ${email}.`)).toBeVisible();
}

test("an invited tenant lands in their unit and the owner sees it occupied", async ({
  page,
  browser,
}) => {
  await ownerWithOrganization(page, "Riverside Estates");
  const propertyUrl = await propertyWithUnits(page, "Riverside Court", ["A1"]);
  await openUnit(page, "A1");
  const email = uniqueEmail();
  await inviteTenantHere(page, email);

  const context = await browser.newContext();
  const tenant = await context.newPage();
  await acceptAsNewUser(tenant, await linkSentTo(email, "/accept-invite"), "Tom Tenant");
  await expect(tenant.getByRole("region", { name: "Your home" })).toContainText(
    "Riverside Court · Unit A1",
  );
  await expect(tenant.getByRole("navigation", { name: "Main" }).getByRole("link")).toHaveText([
    "Dashboard",
    "Maintenance",
  ]);
  await context.close();

  await page.goto(propertyUrl);
  await expect(page.getByRole("row", { name: /A1.*Occupied.*Tom Tenant/ })).toBeVisible();
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Tenants" })
    .click();
  await expect(page.getByRole("row", { name: /Tom Tenant.*Riverside Court.*A1/ })).toBeVisible();
});

test("a tenant can be moved to another unit and their tenancy ended", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Moving Estates");
  const propertyUrl = await propertyWithUnits(page, "Moving Court", ["A1", "A2"]);
  await openUnit(page, "A1");
  const email = uniqueEmail();
  await inviteTenantHere(page, email);

  const context = await browser.newContext();
  const tenant = await context.newPage();
  await acceptAsNewUser(tenant, await linkSentTo(email, "/accept-invite"), "Tina Tenant");

  await page.reload();
  await expect(page.getByText("Tina Tenant")).toBeVisible();
  await page.getByLabel("Move to unit").selectOption({ label: "A2" });
  await page.getByRole("button", { name: "Move tenant" }).click();
  await expect(page.getByLabel("Tenant email")).toBeVisible(); // A1 is vacant again

  await page.goto(propertyUrl);
  await expect(page.getByRole("row", { name: /A1.*Vacant/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /A2.*Occupied.*Tina Tenant/ })).toBeVisible();

  await openUnit(page, "A2");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "End tenancy" }).click();
  await expect(page.getByLabel("Tenant email")).toBeVisible();

  await tenant.reload();
  await expect(tenant.getByText("No organization yet")).toBeVisible();
  await context.close();
});
