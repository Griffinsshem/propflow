import { expect, test } from "./fixtures";
import { registerNewUser } from "./support";

test("visitors see what PropFlow is, and can get started or sign in", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Maintenance requests that don't get lost.",
  );
  const header = page.getByRole("banner");
  await expect(header.getByRole("link", { name: "Go to dashboard" })).toHaveCount(0);

  await header.getByRole("link", { name: "Get started" }).click();
  await expect(page).toHaveURL(/\/register$/);
  await page.goto("/");
  await page.getByRole("banner").getByRole("link", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("signed-in people get a way straight back to their dashboard", async ({ page }) => {
  await registerNewUser(page, "Lena Landing");
  await page.goto("/");
  const header = page.getByRole("banner");
  await expect(header.getByRole("link", { name: "Sign in" })).toHaveCount(0);
  await header.getByRole("link", { name: "Go to dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 360, height: 800 } });

  test("the landing page fits without sideways scrolling", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });
});

test("unknown addresses get a branded page with a way home", async ({ page }) => {
  const response = await page.goto("/no-such-page");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("This page doesn't exist");
  await page.getByRole("link", { name: "Go to the home page" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Maintenance requests that don't get lost.",
  );
});

test("the sign-in page leads back to the home page", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("link", { name: "PropFlow", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Maintenance requests that don't get lost.",
  );
});

test("search engines get rules, a sitemap and a privacy notice", async ({ page, request }) => {
  const robots = await request.get("/robots.txt");
  expect(robots.status()).toBe(200);
  expect(await robots.text()).toContain("Disallow: /dashboard");
  const sitemap = await request.get("/sitemap.xml");
  expect(sitemap.status()).toBe(200);
  expect(await sitemap.text()).toContain("/privacy</loc>");
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Footer" })
    .getByRole("link", { name: "Privacy" })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Privacy");
});
