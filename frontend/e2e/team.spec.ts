import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import {
  createOrganization,
  linkSentTo,
  PASSWORD,
  registerNewUser,
} from "./support";

async function ownerOnTeamPage(
  page: Page,
  organization: string,
): Promise<void> {
  await registerNewUser(page, "Olivia Owner");
  await page.goto("/organizations/new");
  await createOrganization(page, organization);
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Team" })
    .click();
}

async function invite(page: Page, email: string, role: string): Promise<void> {
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Role", { exact: true }).selectOption(role);
  await page.getByRole("button", { name: "Send invitation" }).click();
  await expect(page.getByText(`Invitation sent to ${email}.`)).toBeVisible();
}

test("an owner invites a manager who joins by creating an account", async ({
  page,
  browser,
}) => {
  await ownerOnTeamPage(page, "Riverside Estates");
  const managerEmail = `e2e-${randomUUID()}@example.com`;
  await invite(page, managerEmail, "manager");
  await expect(
    page.getByRole("button", { name: `Revoke invitation for ${managerEmail}` }),
  ).toBeVisible();

  const link = await linkSentTo(managerEmail, "/accept-invite");
  const context = await browser.newContext();
  const manager = await context.newPage();
  await manager.goto(link);
  await expect(
    manager.getByRole("heading", { name: "Join Riverside Estates" }),
  ).toBeVisible();
  await expect(manager.getByLabel("Email")).toHaveValue(managerEmail);
  await manager.getByLabel("Full name").fill("Mary Manager");
  await manager.getByLabel("Password").fill(PASSWORD);
  await manager.getByRole("button", { name: "Create account" }).click();
  await expect(manager).toHaveURL(/\/dashboard$/);
  await expect(manager.getByText("You're signed in as manager.")).toBeVisible();
  await context.close();

  await page.reload();
  await expect(
    page.getByRole("combobox", { name: "Role for Mary Manager" }),
  ).toHaveValue("manager");
  await expect(page.getByText("No pending invitations.")).toBeVisible();
});

test("the last owner can be neither demoted nor deactivated", async ({
  page,
}) => {
  await ownerOnTeamPage(page, "Solo Estates");
  const role = page.getByRole("combobox", { name: "Role for Olivia Owner" });
  const lastOwner = page
    .getByRole("alert")
    .filter({ hasText: "at least one active owner" });

  await role.selectOption("manager");
  await expect(lastOwner).toBeVisible();
  await expect(role).toHaveValue("owner");

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Deactivate Olivia Owner" }).click();
  await expect(lastOwner).toBeVisible();
});

test("an invitation works only for its address and stops working once revoked", async ({
  page,
  browser,
}) => {
  await ownerOnTeamPage(page, "Lakeside Homes");
  const invitee = `e2e-${randomUUID()}@example.com`;
  await invite(page, invitee, "tenant");
  const link = await linkSentTo(invitee, "/accept-invite");

  const context = await browser.newContext();
  const someoneElse = await context.newPage();
  await registerNewUser(someoneElse, "Oscar Other");
  await someoneElse.goto(link);
  await expect(
    someoneElse.getByText(`This invitation is for ${invitee}.`),
  ).toBeVisible();

  await page
    .getByRole("button", { name: `Revoke invitation for ${invitee}` })
    .click();
  await expect(page.getByText("No pending invitations.")).toBeVisible();

  await someoneElse.reload();
  await expect(
    someoneElse.getByRole("heading", { name: "Invitation unavailable" }),
  ).toBeVisible();
  await context.close();
});
