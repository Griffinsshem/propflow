import { expect, test } from "./fixtures";
import { linkSentTo, PASSWORD, registerNewUser, uniqueEmail } from "./support";

const NEW_PASSWORD = "a brand new passphrase";

test("a forgotten password is reset from the emailed link, once", async ({ page }) => {
  const email = await registerNewUser(page, "Rita Reset");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.getByRole("link", { name: "Forgot password?" }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByText("Enter your email address.")).toBeVisible();

  // Unknown and known addresses get the same answer: nobody can probe for accounts.
  const stranger = uniqueEmail();
  await page.getByLabel("Email").fill(stranger);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("status")).toContainText(`If an account exists for ${stranger}`);
  await page.goto("/forgot-password");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("status")).toContainText(`If an account exists for ${email}`);

  const link = await linkSentTo(email, "/reset-password");
  await page.goto(link);
  await expect(
    page.getByRole("heading", { level: 1, name: "Choose a new password" }),
  ).toBeVisible();
  await page.getByLabel("New password", { exact: true }).fill("too short");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByText("Use at least 12 characters.")).toBeVisible();
  await page.getByLabel("New password", { exact: true }).fill(NEW_PASSWORD);
  await page.getByLabel("Confirm new password").fill(`${NEW_PASSWORD}!`);
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByText("The passwords don't match.")).toBeVisible();
  await page.getByLabel("Confirm new password").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByRole("status")).toContainText("Your password has been changed.");

  // The old password no longer works; the new one does.
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
  await page.getByLabel("Password").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  // The same link cannot be used twice.
  await page.goto(link);
  await page.getByLabel("New password", { exact: true }).fill("yet another passphrase");
  await page.getByLabel("Confirm new password").fill("yet another passphrase");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Link unavailable" })).toBeVisible();
});

test("a new account verifies its email from the emailed link", async ({ page }) => {
  const email = await registerNewUser(page, "Vera Verify");
  const banner = page.getByRole("region", { name: "Email verification" });
  await expect(banner).toContainText(email);
  await banner.getByRole("button", { name: "Resend email" }).click();
  await expect(banner.getByRole("status")).toHaveText("We've sent a new link.");

  await page.goto(await linkSentTo(email, "/verify-email"));
  await expect(page.getByRole("heading", { level: 1, name: "Verify your email" })).toBeVisible();
  await page.getByRole("button", { name: "Verify my email" }).click();
  await expect(page.getByRole("status")).toContainText("Your email address is verified.");
  await page.getByRole("link", { name: "Go to your dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("region", { name: "Email verification" })).toHaveCount(0);
});

test("a verification link without a token explains itself", async ({ page }) => {
  await page.goto("/verify-email");
  await expect(page.getByRole("heading", { level: 1, name: "Link unavailable" })).toBeVisible();
  await page.goto("/reset-password");
  await expect(page.getByRole("heading", { level: 1, name: "Link unavailable" })).toBeVisible();
});
