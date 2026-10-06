import { randomUUID } from "node:crypto";

import { expect, type Page } from "@playwright/test";

export const PASSWORD = "correct horse battery staple";

export async function registerNewUser(page: Page, fullName: string): Promise<string> {
  const email = `e2e-${randomUUID()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Full name").fill(fullName);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  return email;
}

export async function createOrganization(page: Page, name: string): Promise<void> {
  await page.getByLabel("Organization name").fill(name);
  await page.getByRole("button", { name: "Create organization" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name })).toBeVisible();
}
