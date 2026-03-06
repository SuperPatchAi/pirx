import { test, expect } from "@playwright/test";

test.describe("Chat", () => {
  test("should redirect unauthenticated users to login", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/login/);
  });
});
