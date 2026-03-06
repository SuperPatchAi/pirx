import { test, expect } from "@playwright/test";

test.describe("Login Flow", () => {
  test("should display login page", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("h1, h2").first()).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test("should show error for invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "bad@test.com");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.click('button[type="submit"]');
    await expect(
      page.locator("text=error").or(page.locator("[role='alert']"))
    ).toBeVisible({ timeout: 5000 });
  });

  test("should have OAuth buttons", async ({ page }) => {
    await page.goto("/login");
    await expect(
      page
        .locator("text=Google")
        .or(page.locator("text=Sign in with Google"))
    ).toBeVisible();
  });
});
