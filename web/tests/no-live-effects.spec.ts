import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { readdirSync } from 'node:fs';

async function denyUnexpected(
  context: BrowserContext,
  page: Page,
): Promise<string[]> {
  const unexpected: string[] = [];
  const origin = 'http://127.0.0.1:4173';
  const assets = new Map(
    readdirSync('dist/assets').map((name) => [
      `/assets/${name}`,
      name.endsWith('.js')
        ? 'script'
        : name.endsWith('.css')
          ? 'stylesheet'
          : 'image',
    ]),
  );
  let documentLoaded = false;
  await context.routeWebSocket('**/*', (socket) => {
    unexpected.push(`blocked websocket ${socket.url()}`);
    socket.close();
  });
  await context.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const initialDocument =
      !documentLoaded &&
      url.pathname === '/' &&
      request.resourceType() === 'document' &&
      request.frame() === page.mainFrame();
    const expectedAsset = assets.get(url.pathname) === request.resourceType();
    if (
      url.origin !== origin ||
      request.method() !== 'GET' ||
      url.search !== '' ||
      (!initialDocument && !expectedAsset)
    ) {
      unexpected.push(`${request.method()} ${request.url()}`);
      await route.abort();
    } else {
      if (initialDocument) documentLoaded = true;
      await route.continue();
    }
  });
  page.on('websocket', (socket) =>
    unexpected.push(`websocket ${socket.url()}`),
  );
  page.on('popup', (popup) => {
    unexpected.push('popup');
    void popup.close();
  });
  page.on('pageerror', (error) => unexpected.push(error.message));
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'sendBeacon', {
      value: () => {
        throw new Error('Unexpected beacon');
      },
    });
  });
  return unexpected;
}

test('request guard denies extra same-origin assets and navigation', async ({
  page,
  context,
}) => {
  const unexpected = await denyUnexpected(context, page);
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('10 matching');
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => {
        const image = new Image();
        image.onerror = () => resolve();
        image.src = '/unexpected.gif';
      }),
  );
  await page.goto('/unexpected-page').catch(() => {});
  expect(unexpected).toEqual([
    'GET http://127.0.0.1:4173/unexpected.gif',
    'GET http://127.0.0.1:4173/unexpected-page',
  ]);
});

test('built assets and interactions have no live effects or executable fixture markup', async ({
  page,
  context,
}) => {
  const unexpected = await denyUnexpected(context, page);
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('10 matching');
  const before = await page.locator('[data-task]').allTextContents();
  await page.getByRole('button', { name: 'Collapse all', exact: true }).click();
  await page.getByRole('button', { name: 'Expand all', exact: true }).click();
  await page.getByRole('button', { name: 'Archive', exact: true }).click();
  await page.getByRole('button', { name: 'Board', exact: true }).click();
  expect(await page.locator('[data-task]').allTextContents()).toEqual(before);
  await expect(page.locator('article img, article script, iframe')).toHaveCount(
    0,
  );
  expect(await page.evaluate(() => 'syntheticInjected' in window)).toBe(false);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([
    'axel.synthetic-board.presentation.v1',
  ]);
  expect(
    await page.evaluate(() =>
      Object.keys(
        JSON.parse(
          localStorage.getItem('axel.synthetic-board.presentation.v1')!,
        ),
      ),
    ),
  ).toEqual(['collapsed', 'stretched']);
  expect(await page.evaluate(() => Object.keys(sessionStorage))).toEqual([]);
  expect(await context.cookies()).toEqual([]);
  expect(
    await page.evaluate(() =>
      navigator.serviceWorker.getRegistrations().then((items) => items.length),
    ),
  ).toBe(0);
  await expect(
    page.getByRole('button', {
      name: /^(Edit|Approve|Submit|Claim|Restore task|Import|Export)$/i,
    }),
  ).toHaveCount(0);
  expect(unexpected).toEqual([]);
});
