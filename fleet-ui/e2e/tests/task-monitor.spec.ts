import { test, expect } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';

test.describe('Task Monitor', () => {
  let taskId: string;

  test.beforeAll(async () => {
    // Create a test task in Supabase
    const supabase = createClient(
      process.env.VITE_SUPABASE_URL || '',
      process.env.VITE_SUPABASE_ANON_KEY || '',
    );
    // Sign in to get auth
    await supabase.auth.signInWithPassword({
      email: process.env.E2E_EMAIL || '',
      password: process.env.E2E_PASSWORD || '',
    });
    const { data } = await supabase.from('tasks').insert({
      user_id: 'd027d2dc-74c9-4ac9-a319-a3dc7f689e35',
      repo: '/test/repo',
      description: 'E2E test task for monitor',
      status: 'running',
      workflow_name: 'default',
      total_tokens: 5000,
      completed_stages: ['plan', 'backend'],
    }).select().single();
    taskId = data?.id;
  });

  test('task monitor page renders', async ({ page }) => {
    if (!taskId) test.skip();
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByTestId('monitor-title')).toBeVisible();
  });

  test('task description displayed', async ({ page }) => {
    if (!taskId) test.skip();
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByTestId('task-description')).toContainText('E2E test task');
  });

  test('pipeline visualizer renders stages', async ({ page }) => {
    if (!taskId) test.skip();
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByTestId('pipeline-visualizer')).toBeVisible();
    await expect(page.getByTestId('stage-plan')).toBeVisible();
    await expect(page.getByTestId('stage-backend')).toBeVisible();
  });

  test('progress bar renders', async ({ page }) => {
    if (!taskId) test.skip();
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByTestId('progress-bar')).toBeVisible();
  });

  test.afterAll(async () => {
    // Cleanup test task
    if (!taskId) return;
    const supabase = createClient(
      process.env.VITE_SUPABASE_URL || '',
      process.env.VITE_SUPABASE_ANON_KEY || '',
    );
    await supabase.auth.signInWithPassword({
      email: process.env.E2E_EMAIL || '',
      password: process.env.E2E_PASSWORD || '',
    });
    await supabase.from('tasks').delete().eq('id', taskId);
  });
});
