import { randomUUID } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

import { expect, type Browser, type Page } from "@playwright/test";

export const PASSWORD = "correct horse battery staple";

export const uniqueEmail = () => `e2e-${randomUUID()}@example.com`;

export async function registerNewUser(page: Page, fullName: string): Promise<string> {
  const email = uniqueEmail();
  await page.goto("/register");
  await page.getByLabel("Full name").fill(fullName);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  // Account creation hashes the password with Argon2, slow by design; under parallel
  // journeys (and the demo's sandbox building) it can take longer than the default 5 s.
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  return email;
}

export async function signIn(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

export async function createOrganization(page: Page, name: string): Promise<void> {
  await page.getByLabel("Organization name").fill(name);
  await page.getByRole("button", { name: "Create organization" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name })).toBeVisible();
}

/** Registers a new owner with a fresh organization; returns the owner's email. */
export async function ownerWithOrganization(page: Page, organization: string): Promise<string> {
  const email = await registerNewUser(page, "Olivia Owner");
  await page.goto("/organizations/new");
  await createOrganization(page, organization);
  return email;
}

export async function inviteFromTeamPage(page: Page, email: string, role: string): Promise<void> {
  await page.goto("/settings/team");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Role", { exact: true }).selectOption(role);
  await page.getByRole("button", { name: "Send invitation" }).click();
  await expect(page.getByText(`Invitation sent to ${email}.`)).toBeVisible();
}

export async function acceptAsNewUser(page: Page, link: string, fullName: string): Promise<void> {
  await page.goto(link);
  await page.getByLabel("Full name").fill(fullName);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  // Account creation hashes the password with Argon2, slow by design; under parallel
  // journeys (and the demo's sandbox building) it can take longer than the default 5 s.
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
}

export async function createProperty(page: Page, name: string): Promise<string> {
  await page.goto("/properties/new");
  await page.getByLabel("Property name").fill(name);
  await page.getByLabel("Address", { exact: true }).fill("1 River Road");
  await page.getByLabel("City", { exact: true }).fill("Nairobi");
  await page.getByRole("button", { name: "Create property" }).click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  return page.url();
}

/**
 * The newest link to `path` emailed to `email`. Requires the API's file email backend
 * (EMAIL_BACKEND=file) writing to the directory named by E2E_MAIL_DIR.
 */
export async function linkSentTo(email: string, path: string): Promise<string> {
  const directory = process.env.E2E_MAIL_DIR;
  if (!directory) throw new Error("Set E2E_MAIL_DIR to the API's EMAIL_FILE_DIR");
  const pattern = new RegExp(`https?://\\S+${path}#token=[A-Za-z0-9_.-]+`);
  for (let attempt = 0; attempt < 50; attempt += 1) {
    const files = (await readdir(directory).catch(() => [] as string[]))
      .filter((name) => name.endsWith(".json"))
      .sort()
      .reverse();
    for (const name of files) {
      const message = JSON.parse(await readFile(join(directory, name), "utf8")) as {
        to: string;
        body: string;
      };
      const link = message.to === email ? pattern.exec(message.body)?.[0] : undefined;
      if (link) return link;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`No email to ${email} containing ${path}`);
}

export async function propertyWithUnits(
  page: Page,
  name: string,
  labels: string[],
): Promise<string> {
  const url = await createProperty(page, name);
  for (const label of labels) {
    await page.getByLabel("Unit label").fill(label);
    await page.getByRole("button", { name: "Add unit" }).click();
    await expect(page.getByText(`Unit ${label} added.`)).toBeVisible();
  }
  return url;
}

/** From a property page: invites a new tenant into `unitLabel`; returns the tenant's signed-in page. */
export async function placeNewTenant(
  page: Page,
  browser: Browser,
  unitLabel: string,
  fullName: string,
): Promise<Page> {
  await page.getByRole("link", { name: unitLabel, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: `Unit ${unitLabel}` })).toBeVisible();
  const email = uniqueEmail();
  await page.getByLabel("Tenant email").fill(email);
  await page.getByRole("button", { name: "Invite tenant" }).click();
  await expect(page.getByText(`Invitation sent to ${email}.`)).toBeVisible();
  const context = await browser.newContext();
  const tenant = await context.newPage();
  await acceptAsNewUser(tenant, await linkSentTo(email, "/accept-invite"), fullName);
  return tenant;
}

export async function reportAsTenant(page: Page, title: string): Promise<void> {
  await page.goto("/maintenance/new");
  await expect(page.getByRole("heading", { level: 1, name: "Report an issue" })).toBeVisible();
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("What's wrong?").fill("Reported by an end-to-end test.");
  await page.getByRole("button", { name: "Submit report" }).click();
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
}

export async function reportAsStaff(
  page: Page,
  property: string,
  title: string,
  priority = "normal",
): Promise<void> {
  await page.goto("/maintenance/new");
  await expect(page.getByRole("heading", { level: 1, name: "Report an issue" })).toBeVisible();
  await page.getByLabel("Property", { exact: true }).selectOption({ label: property });
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Priority").selectOption(priority);
  await page.getByLabel("What's wrong?").fill("Reported by an end-to-end test.");
  await page.getByRole("button", { name: "Submit report" }).click();
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
}

/** Adds a contractor and signs a new person in as them; returns that person's page. */
export async function addContractorWithLogin(
  page: Page,
  browser: Browser,
  name: string,
  specialty: string,
  fullName: string,
): Promise<Page> {
  await page.goto("/contractors/new");
  await expect(page.getByRole("heading", { level: 1, name: "Add a contractor" })).toBeVisible();
  await page.getByLabel("Business name").fill(name);
  await page.getByLabel("Specialty").selectOption(specialty);
  await page.getByRole("button", { name: "Create contractor" }).click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  const email = uniqueEmail();
  await page.getByLabel("Login email").fill(email);
  await page.getByRole("button", { name: "Invite to sign in" }).click();
  await expect(page.getByText(`Invitation sent to ${email}.`)).toBeVisible();
  const context = await browser.newContext();
  const contractor = await context.newPage();
  await acceptAsNewUser(contractor, await linkSentTo(email, "/accept-invite"), fullName);
  return contractor;
}

/** On a submitted request's page: triage it and assign it to `contractorOption`. */
export async function triageAndAssign(page: Page, contractorOption: string): Promise<void> {
  await page
    .getByRole("group", { name: "Status actions" })
    .getByRole("button", { name: "Triage" })
    .click();
  await page.getByLabel("Contractor", { exact: true }).selectOption({ label: contractorOption });
  await page.getByRole("button", { name: "Assign contractor" }).click();
  await expect(page.getByRole("list", { name: "Work orders" })).toContainText("Assigned");
}
