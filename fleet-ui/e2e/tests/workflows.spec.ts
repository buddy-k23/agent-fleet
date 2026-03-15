import { test, expect } from '@playwright/test';

test.describe('Workflow Designer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workflows');
  });

  test('workflow title visible', async ({ page }) => {
    await expect(page.getByTestId('workflow-title')).toBeVisible();
  });

  test('canvas renders', async ({ page }) => {
    await expect(page.getByTestId('workflow-canvas')).toBeVisible();
  });

  test('workflow name editable', async ({ page }) => {
    const nameInput = page.getByTestId('workflow-name').locator('input');
    await expect(nameInput).toBeVisible();
    await nameInput.fill('Custom Pipeline');
    await expect(nameInput).toHaveValue('Custom Pipeline');
  });

  test('export button visible', async ({ page }) => {
    await expect(page.getByTestId('export-btn')).toBeVisible();
  });

  test('save button visible', async ({ page }) => {
    await expect(page.getByTestId('save-btn')).toBeVisible();
  });

  test('default nodes rendered in canvas', async ({ page }) => {
    // React Flow renders nodes as divs inside the canvas
    const canvas = page.getByTestId('workflow-canvas');
    await expect(canvas).toBeVisible();
    // Check for node content text
    await expect(canvas.getByText('Plan')).toBeVisible();
    await expect(canvas.getByText('Backend')).toBeVisible();
    await expect(canvas.getByText('Review')).toBeVisible();
  });
});
