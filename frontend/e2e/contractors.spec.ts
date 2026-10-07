import { expect, test, type Page } from "./fixtures";
import { acceptAsNewUser, linkSentTo, ownerWithOrganization, uniqueEmail } from "./support";

async function addContractor(page: Page, name: string, specialty: string): Promise<void> {
  await page.goto("/contractors/new");
  await expect(page.getByRole("heading", { level: 1, name: "Add a contractor" })).toBeVisible();
  await page.getByLabel("Business name").fill(name);
  await page.getByLabel("Specialty").selectOption(specialty);
  await page.getByRole("button", { name: "Create contractor" }).click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
}

test("an owner adds a contractor and invites them to sign in", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Contractor Estates");
  await page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name: "Contractors" })
    .click();
  await expect(page.getByText("No contractors yet.", { exact: false })).toBeVisible();

  await page.getByRole("link", { name: "Add contractor" }).click();
  await page.getByLabel("Business name").fill("Fixit Plumbing");
  await page.getByLabel("Specialty").selectOption("plumbing");
  await page.getByLabel("Phone (optional)").fill("0712345678");
  await page.getByRole("button", { name: "Create contractor" }).click();
  await expect(page.getByText("Use international format, e.g. +254712345678.")).toBeVisible();
  await page.getByLabel("Phone (optional)").fill("+254712345678");
  await page.getByRole("button", { name: "Create contractor" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Fixit Plumbing" })).toBeVisible();

  await expect(
    page.getByText("This contractor can't sign in yet.", { exact: false }),
  ).toBeVisible();
  const email = uniqueEmail();
  await page.getByLabel("Login email").fill(email);
  await page.getByRole("button", { name: "Invite to sign in" }).click();
  await expect(page.getByText(`Invitation sent to ${email}.`)).toBeVisible();

  const context = await browser.newContext();
  const contractor = await context.newPage();
  await contractor.goto(await linkSentTo(email, "/accept-invite"));
  await expect(contractor.getByText("Contractor", { exact: true })).toBeVisible();
  await acceptAsNewUser(contractor, await linkSentTo(email, "/accept-invite"), "Fred Fixit");
  await expect(contractor.getByText("You're signed in as contractor.")).toBeVisible();
  await expect(contractor.getByRole("navigation", { name: "Main" }).getByRole("link")).toHaveText([
    "Dashboard",
    "Work orders",
  ]);
  await context.close();

  await page.reload();
  await expect(page.getByText("This contractor can sign in.", { exact: false })).toBeVisible();
  await expect(page.getByLabel("Login email")).toHaveCount(0);
});

test("deactivated contractors move to the inactive list", async ({ page }) => {
  await ownerWithOrganization(page, "Roster Estates");
  await addContractor(page, "Sparkle Cleaning", "cleaning");
  await page.getByLabel("Status", { exact: true }).selectOption("inactive");
  await page.getByRole("button", { name: "Save contractor" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();

  await page.goto("/contractors");
  await expect(page.getByRole("heading", { level: 1, name: "Contractors" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Sparkle Cleaning/ })).toHaveCount(0);
  await page.getByRole("button", { name: "Inactive" }).click();
  await expect(page.getByRole("link", { name: /Sparkle Cleaning/ })).toBeVisible();
  await page.getByLabel("Specialty").selectOption("plumbing");
  await expect(page.getByText("No contractors match these filters.")).toBeVisible();
});
