import { randomUUID } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

import { expect, type Page } from "@playwright/test";

export const PASSWORD = "correct horse battery staple";

export async function registerNewUser(
  page: Page,
  fullName: string,
): Promise<string> {
  const email = `e2e-${randomUUID()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Full name").fill(fullName);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  return email;
}

export async function createOrganization(
  page: Page,
  name: string,
): Promise<void> {
  await page.getByLabel("Organization name").fill(name);
  await page.getByRole("button", { name: "Create organization" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name })).toBeVisible();
}

/**
 * The newest link to `path` emailed to `email`. Requires the API's file email backend
 * (EMAIL_BACKEND=file) writing to the directory named by E2E_MAIL_DIR.
 */
export async function linkSentTo(email: string, path: string): Promise<string> {
  const directory = process.env.E2E_MAIL_DIR;
  if (!directory)
    throw new Error("Set E2E_MAIL_DIR to the API's EMAIL_FILE_DIR");
  const pattern = new RegExp(`https?://\\S+${path}#token=[A-Za-z0-9_.-]+`);
  for (let attempt = 0; attempt < 50; attempt += 1) {
    const files = (await readdir(directory).catch(() => [] as string[]))
      .filter((name) => name.endsWith(".json"))
      .sort()
      .reverse();
    for (const name of files) {
      const message = JSON.parse(
        await readFile(join(directory, name), "utf8"),
      ) as {
        to: string;
        body: string;
      };
      const link =
        message.to === email ? pattern.exec(message.body)?.[0] : undefined;
      if (link) return link;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`No email to ${email} containing ${path}`);
}
