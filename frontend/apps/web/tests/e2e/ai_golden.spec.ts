                    import { test, expect } from '@playwright/test';

test('Builder Suggest → Propose → Apply → Run', async ({ page }) => {
  await page.goto('/studio');
  // Enter minimal canvas_state and prompt
  await page.getByTestId('builder-container').getByTestId('builder-canvas').first().fill('{"blueprint":{"nodes":[]}}');
  await page.getByTestId('builder-container').getByTestId('builder-prompt').first().fill('Add an llm node and connect to output');
  await page.getByTestId('builder-container').getByTestId('builder-suggest').click();
  await expect(page.locator('text=Patches JSON').first()).toBeVisible();

  await page.getByTestId('builder-container').getByTestId('builder-propose').click();
  await page.getByRole('button', { name: 'Show diff' }).click();
  await expect(page.locator('text=Proposed changes')).toBeVisible();

  // Apply via dialog when available; otherwise fall back to plain apply
  if (await page.getByTestId('builder-apply-diff').isVisible()) {
    await page.getByTestId('builder-apply-diff').click();
    await page.getByRole('button', { name: 'Confirm' }).click();
  } else {
    await page.getByTestId('builder-container').getByTestId('builder-apply').click();
  }

  // Run
  await page.getByTestId('builder-container').getByTestId('builder-run').click();
  await expect(page.getByTestId('execution-drawer')).toBeVisible();
});
