import { expect, test } from "./fixtures";
import {
  createProperty,
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
  reportAsStaff,
  reportAsTenant,
} from "./support";

test("the owner's dashboard counts link to exactly the matching lists", async ({ page }) => {
  await ownerWithOrganization(page, "Dashboard Estates");
  await createProperty(page, "Dash House");
  await reportAsStaff(page, "Dash House", "Broken boiler", "urgent");
  await reportAsStaff(page, "Dash House", "Loose tile");

  await page.goto("/dashboard");
  await expect(page.getByRole("link", { name: "Properties: 1" })).toBeVisible();
  const operations = page.getByRole("region", { name: "Operations" });
  await operations.getByRole("link", { name: "New requests: 2" }).click();
  await expect(page).toHaveURL(/\/maintenance\?status=submitted$/);
  await expect(page.getByLabel("Status", { exact: true })).toHaveValue("submitted");
  await expect(page.getByRole("link", { name: "Broken boiler" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Loose tile" })).toBeVisible();

  // Acting on one request changes the count the next time the dashboard opens.
  await page.getByRole("link", { name: "Broken boiler" }).click();
  await expect(page).toHaveURL(/\/maintenance\/[0-9a-f-]{36}$/);
  await page
    .getByRole("group", { name: "Status actions" })
    .getByRole("button", { name: "Triage" })
    .click();
  await expect(page.getByText("Triaged", { exact: true })).toBeVisible();
  await page.goto("/dashboard");
  await expect(operations.getByRole("link", { name: "New requests: 1" })).toBeVisible();

  // A filtered list survives a reload, because the filter lives in the address.
  await page.goto("/maintenance?priority=urgent");
  await expect(page.getByLabel("Priority")).toHaveValue("urgent");
  await expect(page.getByRole("link", { name: "Broken boiler" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Loose tile" })).toHaveCount(0);
});

test("a tenant's dashboard counts only their own requests", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Tenant Dash Estates");
  await propertyWithUnits(page, "Tenant Dash Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Tia Tenant");
  await reportAsTenant(tenant, "Dripping tap");
  await reportAsStaff(page, "Tenant Dash Court", "Hallway light");

  await tenant.goto("/dashboard");
  await expect(tenant.getByRole("region", { name: "Your home" })).toContainText(
    "Tenant Dash Court · Unit A1",
  );
  await tenant.getByRole("link", { name: "Submitted: 1" }).click();
  await expect(tenant).toHaveURL(/\/maintenance\?status=submitted$/);
  await expect(tenant.getByRole("link", { name: "Dripping tap" })).toBeVisible();
  await expect(tenant.getByRole("link", { name: "Hallway light" })).toHaveCount(0);
  await tenant.context().close();
});
