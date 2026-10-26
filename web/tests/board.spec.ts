import { expect, test } from '@playwright/test';

test('board, archive, details, history and controls', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText(
    '10 matching tasks in Board.',
  );
  await expect(
    page.getByText('Synthetic read-only demo', { exact: false }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Collapse all', exact: true }).click();
  const first = page.locator('[data-task="demo:orbit/a"]');
  await first
    .getByRole('button', { name: 'Show details:', exact: false })
    .click();
  await expect(
    first.getByRole('heading', { name: 'History · read-only evidence' }),
  ).toBeVisible();
  await expect(first).toContainText('revision 2');
  await page.getByRole('button', { name: 'Archive', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText(
    '2 matching tasks in Archive.',
  );
  await page.getByRole('button', { name: 'Board', exact: true }).click();
  await page
    .getByLabel('repository', { exact: true })
    .selectOption('tiny-atlas');
  await page
    .getByLabel('workstream', { exact: true })
    .selectOption('Observatory');
  await page.getByLabel('status', { exact: true }).selectOption('Backlog');
  await page.getByLabel('type', { exact: true }).selectOption('Task');
  await page.getByLabel('clarity', { exact: true }).selectOption('Clear');
  await page.getByLabel('priority', { exact: true }).selectOption('P0');
  await expect(page.getByRole('status')).toHaveText(
    '1 matching tasks in Board.',
  );
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await page
    .getByLabel('workstream', { exact: true })
    .selectOption('Archived studies');
  await expect(
    page.getByRole('heading', { name: 'No matching tasks', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await page.getByRole('searchbox').fill('星の庭');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText(
    '1 matching tasks in Board.',
  );
  await page.getByLabel('Sort', { exact: true }).selectOption('priority');
  await page.getByRole('button', { name: 'Reset filters' }).click();
  const lane = page.getByRole('region', { name: 'Backlog', exact: true });
  await lane.getByRole('button', { name: 'Stretch lane' }).click();
  await expect(lane).toHaveClass(/stretched/);
  await lane.getByRole('button', { name: 'Restore lane' }).click();
  await expect(lane).not.toHaveClass(/stretched/);
});

test('loading is non-actionable; stale result cannot replace empty; errors retry', async ({
  page,
}, testInfo) => {
  await page.addInitScript(() => {
    const shifts: number[] = [];
    (window as unknown as { shifts: number[] }).shifts = shifts;
    if (PerformanceObserver.supportedEntryTypes.includes('layout-shift'))
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries())
          shifts.push((entry as PerformanceEntry & { value: number }).value);
      }).observe({ type: 'layout-shift', buffered: true });
  });
  await page.goto('/?scenario=slow');
  await expect(page.getByRole('status')).toHaveText('Loading invented tasks…');
  await expect(page.getByRole('searchbox')).toBeDisabled();
  await expect(page.locator('.skeleton')).toHaveCount(6);
  await expect(page.locator('.skeleton button, .skeleton a')).toHaveCount(0);
  await page.getByLabel('Simulated read').selectOption('empty');
  await expect(
    page.getByRole('heading', { name: 'The invented board is empty' }),
  ).toBeVisible();
  await page.waitForTimeout(1500); // Wait beyond the known old slow response.
  await expect(page.locator('[data-task]')).toHaveCount(0);
  await page.getByLabel('Simulated read').selectOption('error');
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  await page.getByRole('button', { name: 'Retry' }).click();
  await expect(page.getByRole('status')).toHaveText(
    '10 matching tasks in Board.',
  );
  await testInfo.attach('layout-shift-observation', {
    body: JSON.stringify(
      await page.evaluate(
        () => (window as unknown as { shifts: number[] }).shifts,
      ),
    ),
    contentType: 'application/json',
  });
});
