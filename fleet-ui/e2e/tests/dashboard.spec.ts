import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('dashboard title visible', async ({ page }) => {
    await expect(page.getByTestId('dashboard-title')).toBeVisible();
  });

  test('4 KPI cards rendered', async ({ page }) => {
    await expect(page.getByTestId('kpi-active')).toBeVisible();
    await expect(page.getByTestId('kpi-completed')).toBeVisible();
    await expect(page.getByTestId('kpi-tokens')).toBeVisible();
    await expect(page.getByTestId('kpi-success')).toBeVisible();
  });

  test('task table rendered', async ({ page }) => {
    await expect(page.getByTestId('task-table')).toBeVisible();
  });

  test('status filter toggles work', async ({ page }) => {
    const filter = page.getByTestId('status-filter');
    await expect(filter).toBeVisible();
    await filter.getByText('Running').click();
    await filter.getByText('Completed').click();
    await filter.getByText('All').click();
  });

  test('sidebar nav visible with all items', async ({ page }) => {
    await expect(page.getByTestId('sidebar')).toBeVisible();
    await expect(page.getByTestId('nav-dashboard')).toBeVisible();
    await expect(page.getByTestId('nav-agents')).toBeVisible();
    await expect(page.getByTestId('nav-workflows')).toBeVisible();
    await expect(page.getByTestId('nav-submit')).toBeVisible();
    await expect(page.getByTestId('nav-settings')).toBeVisible();
  });
});
