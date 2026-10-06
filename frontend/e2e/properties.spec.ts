import { expect, test } from "./fixtures";

import {
  acceptAsNewUser,
  createProperty,
  inviteFromTeamPage,
  linkSentTo,
  ownerWithOrganization,
  signIn,
  uniqueEmail,
} from "./support";

test("an owner builds a property with a building and units", async ({ page }) => {
  await ownerWithOrganization(page, "Riverside Estates");
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Properties" })
    .click();
  await expect(page.getByText("No properties yet.")).toBeVisible();

  await page.getByRole("link", { name: "Add property" }).click();
  await page.getByLabel("Property name").fill("Riverside Court");
  await page.getByLabel("Type").selectOption("residential");
  await page.getByLabel("Address", { exact: true }).fill("12 River Road");
  await page.getByLabel("City", { exact: true }).fill("Nairobi");
  await page.getByRole("button", { name: "Create property" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Riverside Court" })).toBeVisible();

  await page.getByLabel("Building name").fill("Block A");
  await page.getByRole("button", { name: "Add building" }).click();
  await expect(page.getByRole("list", { name: "Buildings" })).toContainText("Block A");

  await page.getByRole("button", { name: "Add unit" }).click();
  await expect(page.getByText("Enter a label.")).toBeVisible();

  await page.getByLabel("Unit label").fill("A1");
  await page.getByLabel("Building", { exact: true }).selectOption({ label: "Block A" });
  await page.getByLabel("Floor").fill("1");
  await page.getByLabel("Bedrooms").fill("2");
  await page.getByRole("button", { name: "Add unit" }).click();
  await expect(page.getByText("Unit A1 added.")).toBeVisible();
  await expect(page.getByRole("row", { name: /A1\s+Block A\s+1\s+2\s+Vacant/ })).toBeVisible();
});

test("a concurrent edit is shown to the second editor instead of overwritten", async ({
  page,
  browser,
}) => {
  const email = await ownerWithOrganization(page, "Conflict Estates");
  const url = await createProperty(page, "Original Name");

  const context = await browser.newContext();
  const other = await context.newPage();
  await signIn(other, email);
  await other.goto(url);
  await other.getByLabel("City", { exact: true }).fill("Mombasa");
  await other.getByRole("button", { name: "Save details" }).click();
  await expect(other.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();

  // The first window still holds the old version.
  await page.getByLabel("Property name").fill("Renamed by me");
  await page.getByRole("button", { name: "Save details" }).click();
  const notice = page.getByRole("alert").filter({ hasText: "Someone else changed this property" });
  await expect(notice).toContainText("City: Mombasa");

  await page.getByRole("button", { name: "Keep my changes" }).click();
  await expect(page.getByLabel("City", { exact: true })).toHaveValue("Mombasa");
  await expect(page.getByLabel("Property name")).toHaveValue("Renamed by me");
  await page.getByRole("button", { name: "Save details" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();

  await other.reload();
  await expect(other.getByRole("heading", { level: 1, name: "Renamed by me" })).toBeVisible();
  await expect(other.getByLabel("City", { exact: true })).toHaveValue("Mombasa");
  await context.close();
});

test("a manager sees only assigned properties and can add units there", async ({
  page,
  browser,
}) => {
  await ownerWithOrganization(page, "Scoped Estates");
  const assignedUrl = await createProperty(page, "Assigned Court");
  await createProperty(page, "Hidden Court");

  const managerEmail = uniqueEmail();
  await inviteFromTeamPage(page, managerEmail, "manager");
  const link = await linkSentTo(managerEmail, "/accept-invite");
  const context = await browser.newContext();
  const manager = await context.newPage();
  await acceptAsNewUser(manager, link, "Mary Manager");

  await manager.goto("/properties");
  await expect(manager.getByText("No properties are assigned to you yet.")).toBeVisible();
  await expect(manager.getByRole("link", { name: "Add property" })).toHaveCount(0);

  await page.goto(assignedUrl);
  await page.getByLabel("Manager", { exact: true }).selectOption({ label: "Mary Manager" });
  await page.getByRole("button", { name: "Assign" }).click();
  await expect(page.getByRole("button", { name: "Unassign Mary Manager" })).toBeVisible();

  await manager.reload();
  await expect(manager.getByRole("link", { name: /Assigned Court/ })).toBeVisible();
  await expect(manager.getByText("Hidden Court")).toHaveCount(0);

  await manager.getByRole("link", { name: /Assigned Court/ }).click();
  await expect(manager.getByRole("button", { name: "Save details" })).toHaveCount(0);
  await manager.getByLabel("Unit label").fill("M1");
  await manager.getByRole("button", { name: "Add unit" }).click();
  await expect(manager.getByRole("row", { name: /M1/ })).toBeVisible();
  await context.close();
});
