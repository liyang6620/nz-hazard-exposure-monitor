import { expect, test } from "@playwright/test";

test("review link previews before one explicit decision without URL token logging", async ({
  page,
}) => {
  const calls: string[] = [];
  await page.route("http://127.0.0.1:8000/review-briefing", async (route) => {
    const request = route.request();
    const method = request.method();
    if (method === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "http://127.0.0.1:4173",
          "Access-Control-Allow-Methods": "GET, POST",
          "Access-Control-Allow-Headers": "X-Review-Token, Accept",
        },
      });
      return;
    }
    expect(request.url()).not.toContain("test-token");
    expect(request.headers()["x-review-token"]).toBe("test-token");
    calls.push(method);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:4173" },
      body:
        method === "GET"
          ? JSON.stringify({ title: "M7.8 Kaikōura", action: "reject" })
          : JSON.stringify({ status: "rejected" }),
    });
  });

  await page.goto("/review#token=test-token");
  await expect(
    page.getByRole("button", { name: "Confirm reject" }),
  ).toBeVisible();
  expect(calls.length).toBeGreaterThanOrEqual(1);
  expect(calls.every((method) => method === "GET")).toBe(true);
  await page.getByRole("button", { name: "Confirm reject" }).click();
  await expect(
    page.getByRole("heading", { name: "Briefing rejected" }),
  ).toBeVisible();
  expect(calls.filter((method) => method === "POST")).toHaveLength(1);
});
