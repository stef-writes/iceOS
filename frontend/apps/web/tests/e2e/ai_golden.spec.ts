import { test, expect } from '@playwright/test';

test('Studio → Frosty assist on Canvas (roles/text)', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Projects' }).click();
  await page.getByRole('button', { name: 'Create Default Project' }).click();
  await page.waitForURL(/\/canvas\?projectId=/);

  await page.getByRole('button', { name: /Open Frosty/i }).click();
  await page.getByPlaceholder('Ask to add/edit/connect/run…').fill('Add an llm node and connect to output');
  await page.getByRole('button', { name: 'Send' }).click();

  const applyBtn = page.getByRole('button', { name: 'Apply' }).first();
  if (await applyBtn.isVisible()) {
    await applyBtn.click();
  }

  await page.getByRole('button', { name: 'Run graph' }).click();
  await expect(page.getByTestId('execution-drawer').or(page.getByTestId('execution-events'))).toBeVisible();
});
