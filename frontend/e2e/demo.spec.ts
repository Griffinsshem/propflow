import { expect, test } from "./fixtures";

test("a visitor explores a private demo, as each person in it", async ({ page }) => {
  test.setTimeout(90_000); // building a sandbox runs a few hundred queries

  await page.goto("/");
  await page.getByRole("button", { name: "Try the live demo" }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 45_000 });

  const banner = page.getByRole("region", { name: "Demo" });
  await expect(banner).toContainText("Private demo");
  await expect(banner).toContainText("no email is ever sent");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Welcome, Demo");
  await expect(page.getByRole("link", { name: "New requests: 1" })).toBeVisible();

  await banner.getByLabel("View as").selectOption("tenant");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Welcome, Tom");
  await expect(page.getByText("Riverside Court · Unit A1")).toBeVisible();

  await page.getByRole("region", { name: "Demo" }).getByLabel("View as").selectOption("contractor");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Welcome, Fred");

  await page
    .getByRole("region", { name: "Demo" })
    .getByRole("button", { name: "Leave the demo" })
    .click();
  await expect(page).not.toHaveURL(/\/dashboard/);
});

test("signed-out visitors are offered the demo", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Try the live demo" })).toBeVisible();
});
