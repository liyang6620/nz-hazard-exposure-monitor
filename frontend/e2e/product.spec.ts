import { expect, test, type Page } from "@playwright/test";

const browserErrors = new WeakMap<Page, string[]>();

test.beforeEach(async ({ page }) => {
  const consoleErrors: string[] = [];
  browserErrors.set(page, consoleErrors);
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto("/");
  await page.waitForLoadState("networkidle");
});

test.afterEach(async ({ page }) => {
  const errors = browserErrors.get(page) ?? [];
  expect(errors, `Unexpected browser errors: ${errors.join("\n")}`).toEqual([]);
});

test("home communicates the product and shows recent exposure data", async ({
  page,
}) => {
  await expect(
    page.getByRole("heading", {
      name: /M7\.8 Kaikōura.*78,564 buildings in damaging shaking/i,
    }),
  ).toBeVisible();
  await expect(page.getByText("Historical replay · as-if-today")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Latest monitored events" }),
  ).toBeVisible();
  await expect(page.getByText("Latest event")).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("table")).not.toContainText("Darfield 2010");
});

test("earthquake detail displays the map alternative, chart and regional table", async ({
  page,
}) => {
  await page.goto("/events/2016p858000");
  await page.waitForLoadState("networkidle");
  await expect(
    page.getByRole("heading", { name: "Shaking and exposure map" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Text alternative to the exposure map"),
  ).toContainText(/MMI/);
  await expect(
    page.getByText(/Official shaking layer|Preliminary estimate/).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Approved event briefing" }),
  ).toBeVisible();
  const briefing = page.frameLocator('iframe[title="Approved event briefing"]');
  await expect(
    briefing.getByRole("heading", {
      name: /M7\.8 Kaikōura.*78,564 buildings in MMI 6\+ shaking/i,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Exposure by MMI band" }),
  ).toBeVisible();
  await expect(
    page.getByText("Buildings by MMI", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("78,564", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Regional exposure at MMI 6+" }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toContainText("46,691");
});

test("mobile navigation and primary content remain usable", async ({
  page,
}, testInfo) => {
  test.skip(!testInfo.project.name.startsWith("mobile"));
  const menu = page.getByRole("button", { name: "Open navigation" });
  await expect(menu).toBeVisible();
  await menu.click();
  await expect(
    page.getByRole("navigation").getByRole("link", { name: "Latest" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /View exposure assessment/i }),
  ).toBeVisible();

  await page.goto("/events/2016p858000");
  await page.waitForLoadState("networkidle");
  const metrics = page.locator(".event-metrics");
  await expect(metrics).toHaveCSS("grid-template-columns", /.+ .+/);
  const first = metrics.locator(".metric-card").first();
  const third = metrics.locator(".metric-card").nth(2);
  expect((await third.boundingBox())?.y).toBeGreaterThan(
    (await first.boundingBox())?.y ?? 0,
  );
});
