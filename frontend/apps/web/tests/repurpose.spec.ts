import { test, expect } from '@playwright/test';

test('Canvas: Repurpose seed → LinkedIn/Twitter/Blog (Suggest → Apply → Run)', async ({ page }) => {
  await page.goto('/canvas');

  // Compose a request
  const input = page.getByPlaceholder('Suggest an edit');
  await input.click();
  await input.fill('Create a workflow to repurpose a seed into LinkedIn, a 5–7 tweet thread, and a 600–800 word blog post. Draft prompts and connect the nodes; aggregate outputs into JSON keys linkedin,twitter,blog. Seed: We launched a new orchestration feature.');

  // Suggest and wait for patches
  await page.getByRole('button', { name: 'Suggest' }).click();
  await expect(page.getByText('Proposed changes:')).toBeVisible();

  // Apply patches
  await page.getByRole('button', { name: 'Apply' }).first().click();

  // Run the full graph
  await page.getByRole('button', { name: 'Run graph' }).click();

  // Expect some events to appear (SSE drawer shows messages)
  const drawer = page.getByTestId('execution-events');
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText(/workflow\.finished|node\.completed/);
});
