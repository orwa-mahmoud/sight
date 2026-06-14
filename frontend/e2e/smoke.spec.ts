import { expect, test } from "@playwright/test";

// Critical-path smoke test. The first three checks need only the app running
// (frontend + backend). The full login flow runs only when demo credentials are
// provided via E2E_EMAIL / E2E_PASSWORD, so the suite is useful with or without
// a seeded account.
test.describe("auth", () => {
  test("unauthenticated visit redirects to the login page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("login page renders email + password fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test("can navigate from login to register", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: /create|register|sign up/i }).click();
    await expect(page).toHaveURL(/\/register$/);
  });

  test("owner can log in and reach the dashboard", async ({ page }) => {
    const email = process.env.E2E_EMAIL;
    const password = process.env.E2E_PASSWORD;
    test.skip(!email || !password, "set E2E_EMAIL and E2E_PASSWORD to run the full login flow");

    await page.goto("/login");
    await page.getByLabel(/email/i).fill(email!);
    await page.getByLabel(/password/i).fill(password!);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).not.toHaveURL(/\/login$/);
  });
});
