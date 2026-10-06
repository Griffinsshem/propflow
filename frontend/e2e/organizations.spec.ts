import { expect, test } from "@playwright/test";

import { createOrganization, registerNewUser } from "./support";

test("an owner creates organizations, switches between them and renames one", async ({
  page,
}) => {
  await registerNewUser(page, "Olivia Owner");
  const nav = page.getByRole("navigation", { name: "Main" });
  const switcher = page.getByLabel("Active organization");

  // Without an organization, only the dashboard is offered.
  await expect(nav.getByRole("link")).toHaveText(["Dashboard"]);

  await page.getByRole("link", { name: "Create an organization" }).click();
  await createOrganization(page, "Riverside Estates");
  await expect(nav.getByRole("link")).toHaveText([
    "Dashboard",
    "Team",
    "Organization",
  ]);
  await expect(page.getByText("You're signed in as owner.")).toBeVisible();

  await page.getByRole("link", { name: "New organization" }).click();
  await createOrganization(page, "Hillside Homes");
  await expect(switcher.locator("option:checked")).toHaveText("Hillside Homes");

  await switcher.selectOption({ label: "Riverside Estates" });
  await expect(
    page.getByRole("heading", { name: "Riverside Estates" }),
  ).toBeVisible();
  await expect(switcher.locator("option:checked")).toHaveText(
    "Riverside Estates",
  );

  await nav.getByRole("link", { name: "Organization" }).click();
  await page.getByLabel("Organization name").fill("Riverside Lettings");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("status")).toHaveText("Saved.");
  await expect(switcher.locator("option:checked")).toHaveText(
    "Riverside Lettings",
  );
});

test("organization names are validated before reaching the API", async ({
  page,
}) => {
  await registerNewUser(page, "Vera Validator");
  await page.goto("/organizations/new");
  await page.getByRole("button", { name: "Create organization" }).click();
  await expect(page.getByText("Enter a name.")).toBeVisible();
  await expect(page.getByLabel("Organization name")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
});
