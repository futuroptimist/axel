import { expect, test } from '@playwright/test';

test('scroll history writes are coalesced without losing immediate Back/Forward position', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await page.addInitScript(() => {
    const original = history.replaceState.bind(history);
    const counts = window as unknown as { historyWrites: number };
    counts.historyWrites = 0;
    history.replaceState = (...args) => {
      counts.historyWrites++;
      original(...args);
    };
  });
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.locator('[data-task="demo:orbit/a"] a').click();
  await expect(page.locator('[data-task="demo:orbit/a"]')).toBeFocused();
  await page.evaluate(() => {
    (window as unknown as { historyWrites: number }).historyWrites = 0;
    scrollTo(0, 1800);
    for (let i = 0; i < 120; i++) dispatchEvent(new Event('scroll'));
  });
  expect(
    await page.evaluate(
      () => (window as unknown as { historyWrites: number }).historyWrites,
    ),
  ).toBeLessThan(5);
  await page.goBack();
  await page.goForward();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(1800);
});

test('history preserves focus changes without scrolling and focused cards', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.getByRole('button', { name: 'Archive', exact: true }).click();
  await page.getByLabel('priority', { exact: true }).focus();
  await page.goBack();
  await page.goForward();
  await expect(page.getByLabel('priority', { exact: true })).toBeFocused();
  await page.getByRole('button', { name: 'Board', exact: true }).click();
  const card = page.locator('[data-task="demo:orbit/a"]');
  await card.getByRole('link').click();
  await expect(card).toBeFocused();
  await page.goBack();
  await page.goForward();
  await expect(card).toBeFocused();
});

test('loading preserves disclosure-summary keyboard focus', async ({
  page,
}) => {
  await page.goto('/?scenario=slow');
  const help = page.locator('[data-focus="help-summary"]');
  await help.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await expect(help).toBeFocused();
  await expect(page.locator('.help')).toHaveAttribute('open', '');
  const directory = page.locator('[data-focus="directory-summary"]');
  await directory.focus();
  await page
    .getByRole('button', { name: 'Collapse all', exact: true })
    .evaluate((button: HTMLButtonElement) => button.click());
  await expect(directory).toBeFocused();
});

test('Back to a failed read restores Retry focus after the error settles', async ({
  page,
}) => {
  await page.goto('/?scenario=error');
  const retry = page.getByRole('button', { name: 'Retry', exact: true });
  await expect(retry).toBeVisible();
  await retry.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.goBack();
  await expect(retry).toBeFocused();
});

test('new keyboard intent cancels a pending history restoration', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto('/?scenario=slow');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.evaluate(() => scrollTo(0, 1800));
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(1800);
  await page
    .getByLabel('Simulated read')
    .evaluate((node: HTMLSelectElement) => {
      node.value = 'empty';
      node.dispatchEvent(new Event('change'));
    });
  await expect(page.getByRole('status')).toContainText('0 matching');
  await page.goBack();
  await expect(page.getByRole('status')).toContainText('Loading');
  await page.keyboard.press('Tab');
  await page.evaluate(() => scrollTo(0, 0));
  await expect(page.getByRole('status')).toContainText('10 matching');
  expect(await page.evaluate(() => scrollY)).toBeLessThan(500);
});

test('Back and Forward defer scroll restoration until a delayed board is ready', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto('/?scenario=slow');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.evaluate(() => scrollTo(0, 1800));
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(1800);
  // Programmatic selection avoids Playwright scrolling the control into view.
  await page
    .getByLabel('Simulated read')
    .evaluate((node: HTMLSelectElement) => {
      node.value = 'empty';
      node.dispatchEvent(new Event('change'));
    });
  await expect(page.getByRole('status')).toContainText('0 matching');
  await page.goBack();
  await expect(page.getByRole('status')).toContainText('10 matching');
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(1800);
  await page.goForward();
  await expect(page.getByRole('status')).toContainText('0 matching');
});

test('scroll events without wheel input cancel pending link jumps', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto('/?scenario=slow&task=demo%3Aidea%2Fl');
  await page.evaluate(() => scrollTo(0, 300));
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(300);
  await expect(page.getByRole('status')).toContainText('10 matching');
  await expect(page.locator('[data-task="demo:idea/l"]')).not.toBeFocused();
  expect(await page.evaluate(() => scrollY)).toBeLessThan(1000);
});

test('links preserve collapsed state, repeated clicks do not add history, Back/Forward restore', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.getByRole('button', { name: 'Collapse all', exact: true }).click();
  const card = page.locator('[data-task="demo:orbit/a"]');
  await card.getByRole('link').click();
  await expect(card).toBeInViewport();
  await expect(card).toBeFocused();
  await expect(card.getByRole('button')).toHaveAttribute(
    'aria-expanded',
    'false',
  );
  const count = await page.evaluate(() => history.length);
  await card.getByRole('link').click();
  expect(await page.evaluate(() => history.length)).toBe(count);
  await page.reload();
  await expect(card.getByRole('button')).toHaveAttribute(
    'aria-expanded',
    'false',
  );
  await page.getByRole('button', { name: 'Dismiss' }).click();
  await expect(page).not.toHaveURL(/task=/);
  await page.goBack();
  await expect(page).toHaveURL(/task=/);
  await expect(card.getByRole('button')).toHaveAttribute(
    'aria-expanded',
    'false',
  );
  await page.goForward();
  await expect(page).not.toHaveURL(/task=/);
});

test('hidden archived target reveals temporarily; Escape restores view and focus', async ({
  page,
}) => {
  await page.goto('/?q=observatory');
  await expect(page.getByRole('status')).toContainText('1 matching');
  await page.getByRole('button', { name: 'Collapse all', exact: true }).click();
  await page
    .getByText('Demo links · includes hidden and archived tasks', {
      exact: true,
    })
    .click();
  const link = page.locator('[data-focus="directory:demo:chart/j"]');
  await link.click();
  const target = page.locator('[data-task="demo:chart/j"]');
  await expect(target).toBeVisible();
  await expect(target).toBeInViewport();
  await expect(target).toBeFocused();
  await expect(target.getByRole('button')).toHaveAttribute(
    'aria-expanded',
    'false',
  );
  await expect(
    page.getByText('Temporarily revealed outside', { exact: false }),
  ).toContainText('Archived');
  await expect(page.getByRole('searchbox')).toHaveValue('observatory');
  await page.keyboard.press('Escape');
  await expect(target).toHaveCount(0);
  await expect(link).toBeFocused();
  await expect(page.getByRole('searchbox')).toHaveValue('observatory');
  await page.goBack();
  await expect(target).toBeVisible();
  await page.goForward();
  await expect(target).toHaveCount(0);
});

test('user scroll cancels a pending deep-link scroll and unknown links dismiss', async ({
  page,
}) => {
  await page.goto('/?scenario=slow&task=demo%3Aidea%2Fl');
  await page.mouse.wheel(0, 500);
  await expect(page.getByRole('status')).toContainText('10 matching');
  await expect(page.locator('[data-task="demo:idea/l"]')).not.toBeFocused();
  await page.goto('/?task=unknown');
  await expect(
    page.getByText('This invented task link was not found.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Dismiss' }).click();
  await expect(page).not.toHaveURL(/task=/);
});
