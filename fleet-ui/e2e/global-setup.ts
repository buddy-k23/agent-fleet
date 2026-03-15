import { test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  const email = process.env.E2E_EMAIL || 'fleetuser1@gmail.com';
  const password = process.env.E2E_PASSWORD || 'testpass123456';

  await page.goto('/login');
  await page.getByTestId('login-email').locator('input').fill(email);
  await page.getByTestId('login-password').locator('input').fill(password);
  await page.getByTestId('login-submit').click();

  // Wait for redirect to dashboard
  await page.waitForURL('/', { timeout: 10000 });
  await page.getByTestId('dashboard-title').waitFor({ timeout: 5000 });

  // Save auth state
  await page.context().storageState({ path: './e2e/.auth/user.json' });
});
