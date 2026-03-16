import { test, expect } from '@playwright/test';

test.describe('Chat', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
  });

  test('chat page renders', async ({ page }) => {
    await expect(page.getByTestId('conversation-list')).toBeVisible();
    await expect(page.getByTestId('message-thread')).toBeVisible();
  });

  test('new chat button visible', async ({ page }) => {
    await expect(page.getByTestId('new-chat-btn')).toBeVisible();
  });

  test('agent selector visible', async ({ page }) => {
    await expect(page.getByTestId('agent-selector')).toBeVisible();
  });

  test('chat input visible', async ({ page }) => {
    await expect(page.getByTestId('chat-input')).toBeVisible();
  });

  test('quick action chips rendered', async ({ page }) => {
    await expect(page.getByText('Review code')).toBeVisible();
    await expect(page.getByText('Plan feature')).toBeVisible();
  });

  test('send button disabled without input', async ({ page }) => {
    await expect(page.getByTestId('send-btn')).toBeDisabled();
  });

  test('empty state shows welcome message', async ({ page }) => {
    await expect(page.getByText('Agent Fleet Chat')).toBeVisible();
  });
});
