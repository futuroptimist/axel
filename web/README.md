# Synthetic board demo

A local, read-only presentation demo with twelve invented tasks. No account,
backend or live board is connected. Every name, ID and history entry is fictional.

## Run locally

Use Node **24.22.1**, pinned in `.node-version`. This security release includes the
[October 2026 Brotli fix](https://nodejs.org/en/blog/release/v24.22.1).

```sh
cd web
npm ci
npm run dev
```

Open the loopback URL printed by Vite. For the built demo:

```sh
npm run build
npm run preview
```

Preview listens on `127.0.0.1:4173`. Development and preview bind loopback only.
The built app uses local assets and an in-memory asynchronous fixture reader;
development HMR is not used in the no-live-effects test.

## Explore

- Board and Archive are separate views; archived tasks can have any status.
- Search includes titles, descriptions, opaque IDs and inert history. The six
  filters combine with search and the selected view. Each facet count omits only
  that facet's own selection. Zero-count and archived-only options remain visible.
- Sorting uses fixture order as a stable tie breaker. Unranked priority comes last.
- Task titles are permanent links. The demo link directory includes hidden and
  archived targets. Linking scrolls without expanding details or resetting saved
  collapsed state. Hidden targets appear temporarily; Dismiss or Escape restores
  the origin. Back and Forward restore route state and saved scroll/focus.
- Collapse/expand and lane stretch/restore are presentation controls. Only those
  preferences persist under `axel.synthetic-board.presentation.v1`. Task content,
  drafts, filter queries and history are not stored in browser storage.
- The simulated-read selector provides normal, delayed, failed and empty responses.
  Retry selects the normal fixture. The latest request alone may publish results.

For example, `?task=demo%3Aorbit%2Fa` links to an invented task. URLs carry filters,
view and target, while collapsed state remains local to the browser.

## Checks

```sh
npm run check
npm run test
npm run build
npx playwright install chromium firefox webkit
npm run test:e2e
```

The development tools are pinned exactly: TypeScript 7.0.2, Vite 8.3.5,
Vitest 5.0.5, Playwright Test 1.64.1, Prettier 3.9.10 and Node types 24.19.2.
`package-lock.json` records resolved versions and integrity hashes. There are no
production runtime dependencies. Tool compatibility was checked against official
npm metadata and [Vite](https://vite.dev/guide/),
[Vitest](https://vitest.dev/guide/) and
[Playwright](https://playwright.dev/docs/intro) documentation.

Browser tests use the built preview, one worker, Chromium, Firefox and WebKit.
They cover widths 320, 390, 768, 1440 and 2560 CSS pixels, keyboard interaction,
visible focus and CSS zoom at 200 percent. CSS zoom is an automated reflow probe,
not a claim of native browser zoom or physical-device testing. Layout shifts are
recorded where the browser exposes the API; no performance improvement or
production threshold is claimed. Test attachments contain invented demo screenshots
and observations only. The CI workflow uploads the synthetic Playwright report and
test results, without publishing a site.

## Deliberate limits

No edit, approval, submission, claim, task archive/restore, import or export is
available. There are no APIs, credentials, remote fonts, analytics, service workers,
PDF previews, authorization engines or worker ownership. History is text evidence,
never executable authority. The fixture model is neither a transport codec nor
proof of migration fidelity. See the [design](../docs/design/web-milestone-one.md)
and [parity ledger](../docs/design/web-parity-ledger.md).
