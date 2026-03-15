import { test, expect } from '@playwright/test';

test.describe('Agent Builder', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/agents');
  });

  test('agents title visible', async ({ page }) => {
    await expect(page.getByTestId('agents-title')).toBeVisible();
  });

  test('agent cards rendered from Supabase', async ({ page }) => {
    // Wait for agents to load
    await page.waitForTimeout(1000);
    const cards = page.locator('[data-testid^="agent-card-"]');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('search filters agents', async ({ page }) => {
    await page.waitForTimeout(1000);
    await page.getByTestId('agent-search').locator('input').fill('Architect');
    const cards = page.locator('[data-testid^="agent-card-"]');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('create agent button opens dialog', async ({ page }) => {
    await page.getByTestId('create-agent-btn').click();
    await expect(page.getByTestId('agent-name-input')).toBeVisible();
    await expect(page.getByTestId('agent-model-input')).toBeVisible();
    await expect(page.getByTestId('agent-prompt-input')).toBeVisible();
  });

  test('model dropdown shows grouped providers', async ({ page }) => {
    await page.getByTestId('create-agent-btn').click();
    await page.getByTestId('agent-model-input').locator('[role="combobox"]').click();
    await expect(page.getByRole('option', { name: 'Anthropic' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'OpenAI' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Local (Ollama)' })).toBeVisible();
  });

  test('tool chips toggle', async ({ page }) => {
    await page.getByTestId('create-agent-btn').click();
    const codeTool = page.getByTestId('tool-code');
    await expect(codeTool).toBeVisible();
    await codeTool.click();
  });

  test('YAML preview updates with form', async ({ page }) => {
    await page.getByTestId('create-agent-btn').click();
    await page.getByTestId('agent-name-input').locator('input').fill('Test Agent');
    const preview = page.getByTestId('yaml-preview');
    await expect(preview).toContainText('Test Agent');
  });
});
