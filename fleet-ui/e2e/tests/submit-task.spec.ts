import { test, expect } from '@playwright/test';

test.describe('Submit Task', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/submit');
  });

  test('submit page renders', async ({ page }) => {
    await expect(page.getByTestId('submit-title')).toBeVisible();
  });

  test('form fields rendered', async ({ page }) => {
    await expect(page.getByTestId('repo-input')).toBeVisible();
    await expect(page.getByTestId('description-input')).toBeVisible();
    await expect(page.getByTestId('workflow-select')).toBeVisible();
  });

  test('submit button disabled when fields empty', async ({ page }) => {
    const btn = page.getByTestId('submit-task-btn');
    await expect(btn).toBeDisabled();
  });

  test('submit button enabled when fields filled', async ({ page }) => {
    await page.getByTestId('repo-input').locator('input').fill('/test/repo');
    await page.getByTestId('description-input').locator('textarea').first().fill('Test task');
    // Wait for workflow dropdown to populate
    await page.waitForTimeout(1000);
    const btn = page.getByTestId('submit-task-btn');
    await expect(btn).toBeEnabled();
  });
});

test.describe('Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('settings title visible', async ({ page }) => {
    await expect(page.getByTestId('settings-title')).toBeVisible();
  });

  test('display name input rendered', async ({ page }) => {
    await expect(page.getByTestId('display-name-input')).toBeVisible();
  });

  test('model registry shows providers', async ({ page }) => {
    await expect(page.getByTestId('model-anthropic')).toBeVisible();
    await expect(page.getByTestId('model-openai')).toBeVisible();
  });

  test('save button works', async ({ page }) => {
    await page.getByTestId('display-name-input').locator('input').fill('E2E Test User');
    await page.getByTestId('save-profile-btn').click();
    await expect(page.getByTestId('save-profile-btn')).toContainText('Saved!');
  });
});
