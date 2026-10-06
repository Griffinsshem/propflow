import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "./fixtures";

const PASSWORD = "correct horse battery staple";

async function registerNewUser(page: Page, fullName = "Erin Example"): Promise<string> {
  const email = `e2e-${randomUUID()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Full name").fill(fullName);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  return email;
}

async function signIn(page: Page, email: string): Promise<void> {
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("a new user can register, sign out and sign back in", async ({ page }) => {
  const email = await registerNewUser(page);
  await expect(page.getByRole("heading", { name: "Welcome, Erin" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await signIn(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("signed-out visitors are sent to sign in, then returned", async ({ page }) => {
  const email = await registerNewUser(page);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard$/);
  await signIn(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("a wrong password gets one generic message", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`nobody-${randomUUID()}@example.com`);
  await page.getByLabel("Password").fill("not the right password");
  await page.getByRole("button", { name: "Sign in" }).click();
  // Filtered by text: Next's route announcer is also role="alert" (empty, for screen readers).
  await expect(
    page.getByRole("alert").filter({ hasText: "Email or password is incorrect." }),
  ).toBeVisible();
});

test("pages carry a nonce-based CSP and the API answers through the proxy", async ({
  page,
  request,
}) => {
  const response = await page.goto("/login");
  const headers = response?.headers() ?? {};
  expect(headers["content-security-policy"]).toMatch(
    /script-src 'self' 'nonce-[^']+' 'strict-dynamic'/,
  );
  expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-powered-by"]).toBeUndefined();

  // With the proxy secret enforced by the API, a 401 (not 403) proves the proxy added it.
  const me = await request.get("/api/v1/auth/me");
  expect(me.status()).toBe(401);
  expect((await me.json()).error.code).toBe("UNAUTHENTICATED");
});
