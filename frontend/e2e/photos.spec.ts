import { expect, test, type Page } from "./fixtures";
import {
  createProperty,
  ownerWithOrganization,
  placeNewTenant,
  propertyWithUnits,
} from "./support";

// A valid 1×1 PNG: the worker decodes, re-encodes and strips it like any real photo.
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

/** Staff choose a property; tenants never do (the API uses their tenancy). */
async function report(page: Page, title: string, property?: string): Promise<void> {
  await page.goto("/maintenance/new");
  await expect(page.getByRole("heading", { level: 1, name: "Report an issue" })).toBeVisible();
  if (property) {
    await page.getByLabel("Property", { exact: true }).selectOption({ label: property });
  }
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("What's wrong?").fill("See the photo.");
  await page.getByRole("button", { name: "Submit report" }).click();
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
}

async function expectPhotoLoaded(page: Page): Promise<void> {
  const photo = page.getByRole("img", { name: "Photo 1" });
  await expect(photo).toBeVisible();
  await expect
    .poll(() => photo.evaluate((element) => (element as HTMLImageElement).naturalWidth))
    .toBeGreaterThan(0);
}

test("a tenant attaches a photo and the owner sees it", async ({ page, browser }) => {
  await ownerWithOrganization(page, "Photo Estates");
  await propertyWithUnits(page, "Photo Court", ["A1"]);
  const tenant = await placeNewTenant(page, browser, "A1", "Pat Photographer");

  await report(tenant, "Cracked window");
  await tenant.getByLabel("Add photos").setInputFiles({
    name: "window.png",
    mimeType: "image/png",
    buffer: PNG,
  });
  const uploads = tenant.getByRole("list", { name: "Photo uploads" });
  await expect(uploads).toContainText("window.png");
  await expect(uploads).toContainText("Ready");
  await expectPhotoLoaded(tenant);
  const requestUrl = tenant.url();
  await tenant.context().close();

  await page.goto(requestUrl);
  await expectPhotoLoaded(page);
});

test("files that are not photos are refused, before and after upload", async ({ page }) => {
  await ownerWithOrganization(page, "Refusal Estates");
  await createProperty(page, "Refusal House");
  await report(page, "Leaking roof", "Refusal House");
  const picker = page.getByLabel("Add photos");
  const uploads = page.getByRole("list", { name: "Photo uploads" });

  // Refused in the browser: not an image type at all.
  await picker.setInputFiles({
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("hi"),
  });
  await expect(uploads).toContainText("Only JPEG, PNG or WebP photos can be added.");

  // Refused by the worker: claims to be a PNG, but its bytes are not an image.
  await picker.setInputFiles({
    name: "fake.png",
    mimeType: "image/png",
    buffer: Buffer.from("this is not an image"),
  });
  await expect(uploads.getByRole("listitem").filter({ hasText: "fake.png" })).toContainText(
    "Rejected",
  );
  await expect(page.getByText("No photos yet.")).toBeVisible();
});
