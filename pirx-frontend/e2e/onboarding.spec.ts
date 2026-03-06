import { test, expect } from "@playwright/test";

test.describe("Onboarding", () => {
  test("should redirect unauthenticated users to login", async ({ page }) => {
    await page.goto("/onboarding/1");
    await expect(page).toHaveURL(/login/);
  });
});
