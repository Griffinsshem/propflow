import { expect, test } from "./fixtures";
import { ownerWithOrganization } from "./support";

test.use({ viewport: { width: 360, height: 800 } });

const OWNER_SECTIONS = [
  "Dashboard",
  "Maintenance",
  "Work orders",
  "Properties",
  "Tenants",
  "Contractors",
  "Team",
  "Organization",
];

test("on a phone, the header is one row and every section is in the menu", async ({ page }) => {
  await ownerWithOrganization(page, "Phone Estates");

  const sidewaysOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(sidewaysOverflow).toBeLessThanOrEqual(0);
  const header = await page.getByRole("banner").boundingBox();
  expect(header?.height ?? Infinity).toBeLessThanOrEqual(64);

  const openMenu = page.getByRole("button", { name: "Open menu" });
  await openMenu.click();
  const menu = page.getByRole("dialog", { name: "Menu" });
  await expect(menu.getByRole("navigation", { name: "Main" }).getByRole("link")).toHaveText(
    OWNER_SECTIONS,
  );
  await expect(menu.getByRole("button", { name: "Close menu" })).toBeFocused();
  const menuOverflow = await menu.evaluate((panel) => panel.scrollWidth - panel.clientWidth);
  expect(menuOverflow).toBeLessThanOrEqual(0);

  await menu.getByRole("link", { name: "Properties" }).click();
  await expect(page).toHaveURL(/\/properties$/);
  await expect(menu).toHaveCount(0);

  await openMenu.click();
  await expect(menu).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await expect(openMenu).toBeFocused();

  await openMenu.click();
  await menu.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
});
