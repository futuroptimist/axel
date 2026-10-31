import { expect, test } from '@playwright/test';

for (const width of [320, 390, 768, 1440, 2560])
  test(`layout at ${width} CSS pixels`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByRole('status')).toContainText('10 matching');
    await page.getByRole('button', { name: 'Expand all', exact: true }).click();
    const overflow = await page.evaluate(() => ({
      document: document.documentElement.scrollWidth > innerWidth,
      controls: [
        ...document.querySelectorAll<HTMLElement>(
          'button,input,select,article',
        ),
      ].filter(
        (node) =>
          node.getBoundingClientRect().right > innerWidth + 1 ||
          node.getBoundingClientRect().left < -1,
      ).length,
    }));
    expect(overflow).toEqual({ document: false, controls: 0 });
    if (width === 390 || width === 1440)
      await testInfo.attach(`synthetic-board-${width}`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: 'image/png',
      });
  });

test('keyboard, labels, focus and 200 percent CSS zoom', async ({
  page,
}, testInfo) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to board' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  await page.getByRole('searchbox').focus();
  await page.keyboard.type('observatory');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status')).toContainText('1 matching');
  expect(
    await page
      .getByRole('searchbox')
      .evaluate((node) => getComputedStyle(node).outlineStyle),
  ).not.toBe('none');
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await page.evaluate(() => {
    document.documentElement.style.zoom = '2';
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await testInfo.attach('synthetic-board-css-zoom-200', {
    body: await page.screenshot(),
    contentType: 'image/png',
  });
});

test('main text and banner contrast exceed WCAG AA text ratio', async ({
  page,
}) => {
  await page.goto('/');
  const pairs = await page.evaluate(() =>
    ['body', '.banner'].map((selector) => {
      const style = getComputedStyle(document.querySelector(selector)!);
      return [
        style.color,
        selector === 'body'
          ? getComputedStyle(document.documentElement).backgroundColor
          : style.backgroundColor,
      ];
    }),
  );
  const luminance = (color: string) =>
    color
      .match(/\d+/g)!
      .slice(0, 3)
      .map(Number)
      .map((value) => value / 255)
      .map((value) =>
        value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
      )
      .reduce(
        (sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index]!,
        0,
      );
  for (const [foreground, background] of pairs) {
    const values = [luminance(foreground!), luminance(background!)].sort(
      (a, b) => b - a,
    );
    expect((values[0]! + 0.05) / (values[1]! + 0.05)).toBeGreaterThanOrEqual(
      4.5,
    );
  }
});
