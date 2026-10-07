import { expect, test, type Page } from "./fixtures";
import {
  createProperty,
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
  reportAsStaff,
  reportAsTenant,
} from "./support";

const isoDay = (offsetDays: number) =>
  new Date(Date.now() + offsetDays * 86_400_000).toISOString().slice(0, 10);

async function addContractor(page: Page, name: string, specialty: string, inactive = false) {
  await page.goto("/contractors/new");
  await expect(page.getByRole("heading", { level: 1, name: "Add a contractor" })).toBeVisible();
  await page.getByLabel("Business name").fill(name);
  await page.getByLabel("Specialty").selectOption(specialty);
  await page.getByRole("button", { name: "Create contractor" }).click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  if (inactive) {
    await page.getByLabel("Status", { exact: true }).selectOption("inactive");
    await page.getByRole("button", { name: "Save contractor" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();
  }
}

async function triageAndAssign(page: Page, contractor: string): Promise<void> {
  await page
    .getByRole("group", { name: "Status actions" })
    .getByRole("button", { name: "Triage" })
    .click();
  await page.getByLabel("Contractor", { exact: true }).selectOption({ label: contractor });
  await page.getByRole("button", { name: "Assign contractor" }).click();
  await expect(page.getByRole("list", { name: "Work orders" })).toContainText("Assigned");
}

test("staff assign a triaged request to an active contractor", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Assign Estates");
  await addContractor(page, "Fixit Plumbing", "plumbing");
  await addContractor(page, "Old Builders", "carpentry", true);
  await propertyWithUnits(page, "Assign Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Tom Tenant");
  await reportAsTenant(tenant, "Leaking pipe");

  await page.goto(tenant.url());
  const section = page.getByRole("region", { name: "Work orders" });
  await expect(section).toContainText("Triage this request before assigning a contractor.");
  await page
    .getByRole("group", { name: "Status actions" })
    .getByRole("button", { name: "Triage" })
    .click();

  const contractor = page.getByLabel("Contractor", { exact: true });
  await expect(contractor.locator("option", { hasText: "Old Builders" })).toHaveCount(0);
  await contractor.selectOption({ label: "Fixit Plumbing (Plumbing)" });
  await page.getByLabel("Due date (optional)").fill(isoDay(-2));
  await page.getByRole("button", { name: "Assign contractor" }).click();
  await expect(page.getByText("Choose today or a later date.")).toBeVisible();

  await page.getByLabel("Due date (optional)").fill(isoDay(7));
  await page.getByLabel("Instructions (optional)").fill("Bring a 15 mm compression fitting.");
  await page.getByRole("button", { name: "Assign contractor" }).click();
  const orders = section.getByRole("list", { name: "Work orders" });
  await expect(orders).toContainText("Fixit Plumbing");
  await expect(orders).toContainText("Assigned");
  await expect(page.getByRole("button", { name: "Assign contractor" })).toHaveCount(0);
  await expect(page.getByRole("list", { name: "Activity" })).toContainText(
    "moved this from Triaged to Assigned",
  );

  await tenant.reload();
  await expect(tenant.getByRole("list", { name: "Activity" })).toContainText(
    "moved this from Triaged to Assigned",
  );
  await expect(tenant.getByRole("region", { name: "Work orders" })).toHaveCount(0);
  await tenant.context().close();
});

test("cancelling a work order returns the request to triage", async ({ page }) => {
  await ownerWithOrganization(page, "Cancel Estates");
  await addContractor(page, "Quick Electric", "electrical");
  await createProperty(page, "Cancel House");
  await reportAsStaff(page, "Cancel House", "Dead socket");
  await triageAndAssign(page, "Quick Electric (Electrical)");

  await page.getByRole("link", { name: "Quick Electric" }).click();
  await expect(page).toHaveURL(/\/work-orders\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1, name: "Dead socket" })).toBeVisible();
  const actions = page.getByRole("group", { name: "Work order actions" });
  await expect(actions.getByRole("button")).toHaveText([
    "Accept job",
    "Decline job",
    "Cancel work order",
  ]);
  await actions.getByRole("button", { name: "Cancel work order" }).click();
  await page
    .getByLabel("Why is the work order being cancelled?")
    .fill("The contractor is unavailable");
  await page.getByRole("button", { name: "Cancel work order" }).click();
  await expect(page.getByText("Cancelled", { exact: true })).toBeVisible();
  await expect(page.getByRole("list", { name: "Work order history" })).toContainText(
    "Reason: The contractor is unavailable",
  );

  await page.getByRole("link", { name: "Open the maintenance request" }).click();
  await expect(page.getByRole("list", { name: "Activity" })).toContainText(
    "moved this from Assigned to Triaged",
  );
  await expect(page.getByRole("button", { name: "Assign contractor" })).toBeVisible();

  await page.goto("/work-orders");
  await expect(page.getByRole("heading", { level: 1, name: "Work orders" })).toBeVisible();
  await page.getByLabel("Status", { exact: true }).selectOption("cancelled");
  await expect(page.getByRole("link", { name: "Dead socket" })).toBeVisible();
  await page.getByLabel("Status", { exact: true }).selectOption("assigned");
  await expect(page.getByText("No work orders match these filters.")).toBeVisible();
});
