import { expect, test } from "./fixtures";
import {
  createProperty,
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
  reportAsStaff,
  reportAsTenant,
  signIn,
} from "./support";

test("the owner works a tenant's request through the workflow while the tenant follows", async ({
  page,
  browser,
}) => {
  await ownerWithOrganization(page, "Workflow Estates");
  await propertyWithUnits(page, "Workflow Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Tom Tenant");
  await reportAsTenant(tenant, "Broken heater");
  await expect(tenant.getByRole("group", { name: "Status actions" })).toHaveCount(0);

  await page.goto("/maintenance");
  await expect(page.getByRole("heading", { level: 1, name: "Maintenance" })).toBeVisible();
  await page.getByLabel("Status", { exact: true }).selectOption("submitted");
  await page.getByRole("link", { name: "Broken heater" }).click();

  const actions = page.getByRole("group", { name: "Status actions" });
  await expect(actions.getByRole("button")).toHaveText(["Triage", "Close without fixing"]);
  for (const [button, status] of [
    ["Triage", "Triaged"],
    ["Mark as assigned", "Assigned"],
    ["Start work", "In progress"],
  ]) {
    await actions.getByRole("button", { name: button }).click();
    await expect(page.getByText(status, { exact: true })).toBeVisible();
  }

  await actions.getByRole("button", { name: "Put on hold" }).click();
  await page.getByRole("button", { name: "Put on hold" }).click();
  await expect(page.getByText("Give a reason.")).toBeVisible();
  await page.getByLabel("What is the work waiting for?").fill("A replacement part");
  await page.getByRole("button", { name: "Put on hold" }).click();
  await expect(page.getByText("Waiting", { exact: true })).toBeVisible();
  const activity = page.getByRole("list", { name: "Activity" });
  await expect(activity).toContainText("moved this from In progress to Waiting");
  await expect(activity).toContainText("Reason: A replacement part");

  await tenant.reload();
  await expect(tenant.getByText("Waiting", { exact: true })).toBeVisible();
  await expect(tenant.getByRole("list", { name: "Activity" })).toContainText(
    "Reason: A replacement part",
  );
  await expect(tenant.getByRole("group", { name: "Status actions" })).toHaveCount(0);
  await tenant.context().close();
});

test("acting on a request someone else just changed explains what happened", async ({
  page,
  browser,
}) => {
  const email = await ownerWithOrganization(page, "Race Estates");
  await createProperty(page, "Race House");
  await reportAsStaff(page, "Race House", "Blocked drain");
  const requestUrl = page.url();

  const context = await browser.newContext();
  const other = await context.newPage();
  await signIn(other, email);
  await other.goto(requestUrl);
  await other
    .getByRole("group", { name: "Status actions" })
    .getByRole("button", { name: "Triage" })
    .click();
  await expect(other.getByText("Triaged", { exact: true })).toBeVisible();
  await context.close();

  // This window still shows the request as submitted.
  await page
    .getByRole("group", { name: "Status actions" })
    .getByRole("button", { name: "Triage" })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Someone else updated this request" }),
  ).toBeVisible();
  await expect(page.getByText("Triaged", { exact: true })).toBeVisible();
  await expect(
    page
      .getByRole("group", { name: "Status actions" })
      .getByRole("button", { name: "Mark as assigned" }),
  ).toBeVisible();
});

test("the inbox filters by priority", async ({ page }) => {
  await ownerWithOrganization(page, "Filter Estates");
  await createProperty(page, "Filter House");
  await reportAsStaff(page, "Filter House", "Small drip", "low");
  await reportAsStaff(page, "Filter House", "Gas smell", "urgent");

  await page.goto("/maintenance");
  await expect(page.getByRole("link", { name: "Small drip" })).toBeVisible();
  await page.getByLabel("Priority").selectOption("urgent");
  await expect(page.getByRole("link", { name: "Gas smell" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Small drip" })).toHaveCount(0);
  await page.getByLabel("Status", { exact: true }).selectOption("closed");
  await expect(page.getByText("No requests match these filters.")).toBeVisible();
});
