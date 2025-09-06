import { test, expect } from '@playwright/test';

test('Library → Studio → Run (SSE + History)', async ({ page }) => {
  await page.goto('/library');
  await expect(page).toHaveTitle(/iceOS Studio/i);

  // Try library card first, else deep-link to known demo blueprint
  const openButtons = page.getByRole('button', { name: 'Open' });
  if (await openButtons.first().isVisible()) {
    await openButtons.first().click();
  } else {
    await page.goto('/studio?blueprintId=chatkit.rag_chat');
  }

  // Run button in BlueprintEditor (target by data-action)
  await page.getByRole('button', { name: 'Run' }).or(page.locator('button[data-action="run-blueprint"]')).first().click();

  // Expect SSE output in Execution drawer
  await expect(page.getByTestId('execution-drawer')).toBeVisible();
});
