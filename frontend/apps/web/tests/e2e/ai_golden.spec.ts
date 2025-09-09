import { test, expect } from '@playwright/test';

test('Workspaces → New Workflow → Canvas run (roles/text)', async ({ page }) => {
  await page.goto('/workspaces');
  // New Workspace
  await page.getByRole('button', { name: 'New Workspace' }).click();

  // New Project in first workspace row
  await page.getByRole('button', { name: 'New Project' }).first().click();

  // New Workflow opens Canvas
  await page.getByRole('button', { name: 'New Workflow' }).first().click();
  await expect(page).toHaveURL(/\/canvas\?/);

  // Add a node via palette
  await page.getByRole('button', { name: 'Add node' }).click();
  await page.getByRole('button', { name: /^LLM$/ }).click();

  // Run workflow
  await page.getByRole('button', { name: 'Run workflow' }).click();
  await expect(page.locator('text=Execution')).toBeVisible({ timeout: 30000 });
});
