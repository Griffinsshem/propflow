import { expect, test, type Page } from "./fixtures";
import {
  createProperty,
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
} from "./support";

async function postComment(page: Page, text: string): Promise<void> {
  await page.getByLabel("Add a comment").fill(text);
  await page.getByRole("button", { name: "Post comment" }).click();
  await expect(page.getByRole("list", { name: "Activity" })).toContainText(text);
  await expect(page.getByLabel("Add a comment")).toHaveValue("");
}

test("the tenant and the owner talk on the request, in order", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Chatty Estates");
  await propertyWithUnits(page, "Chatty Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Tom Tenant");

  await tenant.goto("/maintenance/new");
  await expect(tenant.getByRole("heading", { level: 1, name: "Report an issue" })).toBeVisible();
  await tenant.getByLabel("Title").fill("No hot water");
  await tenant.getByLabel("What's wrong?").fill("Since this morning.");
  await tenant.getByRole("button", { name: "Submit report" }).click();
  await expect(tenant.getByRole("heading", { level: 1, name: "No hot water" })).toBeVisible();
  await expect(tenant.getByRole("list", { name: "Activity" })).toContainText(
    "Tom Tenant reported this issue",
  );

  await page.goto(tenant.url());
  await expect(page.getByRole("heading", { level: 1, name: "No hot water" })).toBeVisible();
  await page.getByRole("button", { name: "Post comment" }).click();
  await expect(page.getByText("Write a comment first.")).toBeVisible();
  await postComment(page, "A plumber will visit Thursday.");

  await tenant.reload();
  const entries = tenant.getByRole("list", { name: "Activity" }).getByRole("listitem");
  await expect(entries).toHaveCount(2);
  await expect(entries.nth(0)).toContainText("Tom Tenant reported this issue");
  await expect(entries.nth(1)).toContainText("Olivia Owner");
  await expect(entries.nth(1)).toContainText("A plumber will visit Thursday.");
  await postComment(tenant, "Thank you, I'll be home.");
  await tenant.context().close();

  await page.reload();
  const ownerView = page.getByRole("list", { name: "Activity" }).getByRole("listitem");
  await expect(ownerView).toHaveCount(3);
  await expect(ownerView.nth(2)).toContainText("Tom Tenant");
  await expect(ownerView.nth(2)).toContainText("Thank you, I'll be home.");
});

test("comments are shown exactly as typed, never as markup", async ({ page }) => {
  await ownerWithOrganization(page, "Markup Estates");
  await createProperty(page, "Markup House");
  await page.goto("/maintenance/new");
  await expect(page.getByRole("heading", { level: 1, name: "Report an issue" })).toBeVisible();
  await page.getByLabel("Property", { exact: true }).selectOption({ label: "Markup House" });
  await page.getByLabel("Title").fill("Flickering lights");
  await page.getByLabel("What's wrong?").fill("In the stairwell.");
  await page.getByRole("button", { name: "Submit report" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Flickering lights" })).toBeVisible();

  await postComment(page, "<b>not bold</b>");
  const comment = page.getByRole("list", { name: "Activity" }).getByRole("listitem").last();
  await expect(comment).toContainText("<b>not bold</b>");
  await expect(comment.locator("b")).toHaveCount(0);
});
