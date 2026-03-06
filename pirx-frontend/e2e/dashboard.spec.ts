import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test("should redirect unauthenticated users to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/login/);
  });
});
