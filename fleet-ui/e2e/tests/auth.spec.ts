import { test, expect } from '@playwright/test';

test.describe('Auth Flow', () => {
  test.use({ storageState: { cookies: [], origins: [] } }); // No auth for these tests

  test('login page renders', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByTestId('login-title')).toBeVisible();
    await expect(page.getByTestId('login-email')).toBeVisible();
    await expect(page.getByTestId('login-password')).toBeVisible();
    await expect(page.getByTestId('login-submit')).toBeVisible();
  });

  test('signup page renders', async ({ page }) => {
    await page.goto('/signup');
    await expect(page.getByTestId('signup-title')).toBeVisible();
    await expect(page.getByTestId('signup-email')).toBeVisible();
    await expect(page.getByTestId('signup-password')).toBeVisible();
    await expect(page.getByTestId('signup-submit')).toBeVisible();
  });

  test('protected routes redirect to login', async ({ page }) => {
    await page.goto('/');
    await page.waitForURL('/login');
    await expect(page.getByTestId('login-title')).toBeVisible();
  });

  test('invalid credentials show error', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('login-email').locator('input').fill('wrong@email.com');
    await page.getByTestId('login-password').locator('input').fill('wrongpassword');
    await page.getByTestId('login-submit').click();
    await expect(page.getByTestId('login-error')).toBeVisible({ timeout: 5000 });
  });

  test('successful login redirects to dashboard', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('login-email').locator('input').fill(process.env.E2E_EMAIL || '');
    await page.getByTestId('login-password').locator('input').fill(process.env.E2E_PASSWORD || '');
    await page.getByTestId('login-submit').click();
    await page.waitForURL('/', { timeout: 10000 });
    await expect(page.getByTestId('dashboard-title')).toBeVisible();
  });
});

test.describe('Auth — Authenticated', () => {
  test('logout returns to login page', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('nav-logout').click();
    await page.waitForURL('/login', { timeout: 5000 });
    await expect(page.getByTestId('login-title')).toBeVisible();
  });
});
