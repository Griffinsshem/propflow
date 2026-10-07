import { expect, test } from "./fixtures";
import {
  addContractorWithLogin,
  createProperty,
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
  reportAsStaff,
  reportAsTenant,
  triageAndAssign,
} from "./support";

test("a contractor takes a tenant's leak from assignment to completion", async ({
  page,
  browser,
}) => {
  await ownerWithOrganization(page, "Lifecycle Estates");
  const contractor = await addContractorWithLogin(
    page,
    browser,
    "Fixit Plumbing",
    "plumbing",
    "Fred Fixit",
  );
  await propertyWithUnits(page, "Lifecycle Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Tom Tenant");
  await reportAsTenant(tenant, "Leaking pipe");
  await page.goto(tenant.url());
  await triageAndAssign(page, "Fixit Plumbing (Plumbing)");

  // The contractor finds the job on their dashboard and works it.
  await contractor.goto("/dashboard");
  const waiting = contractor.getByRole("list", { name: "Waiting for you" });
  await expect(waiting).toContainText("Leaking pipe");
  await waiting.getByRole("link", { name: "Leaking pipe" }).click();
  await expect(contractor.getByRole("heading", { level: 1, name: "Leaking pipe" })).toBeVisible();
  await expect(contractor.getByRole("link", { name: "Open the maintenance request" })).toHaveCount(
    0,
  );

  const actions = contractor.getByRole("group", { name: "Work order actions" });
  await expect(actions.getByRole("button")).toHaveText(["Accept job", "Decline job"]);
  await actions.getByRole("button", { name: "Accept job" }).click();
  await expect(contractor.getByText("Accepted", { exact: true })).toBeVisible();
  await actions.getByRole("button", { name: "Start job" }).click();
  await expect(contractor.getByText("In progress", { exact: true })).toBeVisible();

  await tenant.reload();
  await expect(tenant.getByRole("list", { name: "Activity" })).toContainText(
    "moved this from Assigned to In progress",
  );

  await actions.getByRole("button", { name: "Mark job complete" }).click();
  await expect(contractor.getByText("Completed", { exact: true })).toBeVisible();
  await expect(actions).toHaveCount(0);

  // Completing the job does not resolve the request: the owner checks and closes it.
  await page.reload();
  const status = page.getByRole("group", { name: "Status actions" });
  await status.getByRole("button", { name: "Mark resolved" }).click();
  await expect(page.getByText("Resolved", { exact: true })).toBeVisible();
  await status.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.getByText("Closed", { exact: true })).toBeVisible();

  // The tenant can follow every step.
  await tenant.reload();
  await expect(tenant.getByText("Closed", { exact: true })).toBeVisible();
  const activity = tenant.getByRole("list", { name: "Activity" });
  for (const step of [
    "reported this issue",
    "from Submitted to Triaged",
    "from Triaged to Assigned",
    "from Assigned to In progress",
    "from In progress to Resolved",
    "from Resolved to Closed",
  ]) {
    await expect(activity).toContainText(step);
  }
  await tenant.context().close();
  await contractor.context().close();
});

test("a contractor sees only their own jobs", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Privacy Estates");
  const first = await addContractorWithLogin(page, browser, "First Fix", "general", "Fiona First");
  const second = await addContractorWithLogin(page, browser, "Second Fix", "general", "Sam Second");
  await createProperty(page, "Privacy House");
  await reportAsStaff(page, "Privacy House", "Squeaky door");
  await triageAndAssign(page, "First Fix (General)");
  await page.getByRole("link", { name: "First Fix" }).click();
  await expect(page).toHaveURL(/\/work-orders\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1, name: "Squeaky door" })).toBeVisible();
  const workOrderUrl = page.url();

  await first.goto("/dashboard");
  await expect(first.getByRole("list", { name: "Waiting for you" })).toContainText("Squeaky door");

  await second.goto("/dashboard");
  await expect(second.getByText("No new jobs.")).toBeVisible();
  await second.goto("/work-orders");
  await expect(second.getByText("No jobs assigned to you yet.")).toBeVisible();
  await second.goto(workOrderUrl);
  await expect(
    second.getByText("This work order doesn't exist, or it isn't visible to you."),
  ).toBeVisible();

  await first.context().close();
  await second.context().close();
});
