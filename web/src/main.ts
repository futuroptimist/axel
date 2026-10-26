import './styles.css';
import {
  BoardLoader,
  createFixtureReader,
  type LoadState,
} from './fixture-reader';
import {
  readPreferences,
  readRoute,
  routeUrl,
  savePreferences,
  type Route,
} from './navigation';
import { render, type Actions } from './render';

const root = document.querySelector<HTMLElement>('#app')!;
let route = readRoute(new URL(location.href));
let draftSearch = route.view.search;
let state: LoadState = { kind: 'loading' };
const storage = {
  getItem(key: string) {
    return localStorage.getItem(key);
  },
  setItem(key: string, value: string) {
    localStorage.setItem(key, value);
  },
};
let preferences = readPreferences(storage);
let navigationGeneration = 0;
let pendingScroll = route.target !== null;
interface Snapshot {
  url: string;
  y: number;
  focus: string | null;
}
interface Entry {
  snapshot?: Snapshot;
  origin?: Snapshot;
}
let pendingRestore: Snapshot | undefined;
function entry(): Entry {
  return (history.state as Entry | null) ?? {};
}
function focusKey(): string | null {
  return (document.activeElement as HTMLElement | null)?.dataset.focus ?? null;
}
function snapshot(): Snapshot {
  return {
    url: location.pathname + location.search,
    y: scrollY,
    focus: focusKey(),
  };
}
function savePosition(): void {
  history.replaceState({ ...entry(), snapshot: snapshot() }, '');
}
function findFocus(key: string): HTMLElement | undefined {
  return [...document.querySelectorAll<HTMLElement>('[data-focus]')].find(
    (node) => node.dataset.focus === key,
  );
}
function restoreFocus(key: string | null): void {
  if (!key) return;
  const node = findFocus(key);
  // A directory link may be inside a closed disclosure after rendering.
  const details = node?.closest('details');
  if (details && node?.tagName !== 'SUMMARY') details.open = true;
  node?.focus({ preventScroll: true });
}
function paint(restore?: Snapshot): void {
  if (restore) pendingRestore = restore;
  const focus = focusKey();
  const helpOpen = document.querySelector<HTMLDetailsElement>('.help')?.open;
  const directoryOpen =
    document.querySelector<HTMLDetailsElement>('.directory')?.open;
  render(root, route, state, preferences, actions, draftSearch);
  const help = document.querySelector<HTMLDetailsElement>('.help');
  if (help) help.open = Boolean(helpOpen);
  const directory = document.querySelector<HTMLDetailsElement>('.directory');
  if (directory) directory.open = Boolean(directoryOpen);
  restoreFocus(focus);
  const generation = ++navigationGeneration;
  requestAnimationFrame(() => {
    if (generation !== navigationGeneration) return;
    if (pendingRestore && state.kind !== 'loading') {
      const position = pendingRestore;
      pendingRestore = undefined;
      scrollTo(0, position.y);
      restoreFocus(position.focus);
      savePosition();
      return;
    }
    if (pendingScroll && state.kind === 'ready' && route.target !== null) {
      const target = [
        ...document.querySelectorAll<HTMLElement>('[data-task]'),
      ].find((node) => node.dataset.task === route.target);
      pendingScroll = false;
      target?.scrollIntoView({ block: 'center', behavior: 'instant' });
      target?.focus({ preventScroll: true });
    }
    if (state.kind !== 'loading') savePosition();
  });
}
function navigate(next: Route, origin?: Snapshot, preserveDraft = false): void {
  savePosition();
  pendingRestore = undefined;
  const previousScenario = route.scenario;
  history.pushState(origin ? { origin } : {}, '', routeUrl(next));
  route = next;
  if (!preserveDraft) draftSearch = route.view.search;
  pendingScroll = route.target !== null;
  if (previousScenario !== next.scenario) void loader.load(next.scenario);
  else paint();
}
function persist(): void {
  savePreferences(storage, preferences);
  paint();
}
const actions: Actions = {
  view(view, preserveDraft) {
    navigate({ ...route, view, target: null }, undefined, preserveDraft);
  },
  searchDraft(value) {
    draftSearch = value;
  },
  scenario(scenario) {
    navigate({ ...route, scenario });
  },
  retry() {
    navigate({ ...route, scenario: 'normal' });
  },
  link(id) {
    if (route.target === id) {
      pendingScroll = true;
      paint();
      return;
    }
    navigate({ ...route, target: id }, entry().origin ?? snapshot());
  },
  dismiss() {
    const origin = entry().origin;
    const next = origin
      ? readRoute(new URL(origin.url, location.origin))
      : { ...route, target: null };
    navigate({ ...next, target: null });
    if (origin) paint(origin);
  },
  toggle(id) {
    preferences = {
      ...preferences,
      collapsed: preferences.collapsed.includes(id)
        ? preferences.collapsed.filter((value) => value !== id)
        : [...preferences.collapsed, id],
    };
    persist();
  },
  all(collapse) {
    if (state.kind === 'ready') {
      preferences = {
        ...preferences,
        collapsed: collapse ? state.board.map((task) => task.id) : [],
      };
      persist();
    }
  },
  stretch(status) {
    preferences = {
      ...preferences,
      stretched: preferences.stretched === status ? null : status,
    };
    persist();
  },
};
const loader = new BoardLoader(createFixtureReader(), (next) => {
  state = next;
  paint();
});
history.scrollRestoration = 'manual';
addEventListener('focusin', () => {
  if (state.kind !== 'loading' && !pendingRestore && !pendingScroll)
    savePosition();
});
addEventListener(
  'pointerdown',
  () => {
    pendingScroll = false;
    pendingRestore = undefined;
    navigationGeneration++;
  },
  { capture: true },
);
addEventListener('popstate', () => {
  const oldScenario = route.scenario;
  route = readRoute(new URL(location.href));
  draftSearch = route.view.search;
  pendingScroll = false;
  pendingRestore = entry().snapshot;
  if (oldScenario !== route.scenario) void loader.load(route.scenario);
  paint(entry().snapshot);
});
addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && route.target !== null) actions.dismiss();
  if (
    [
      'Tab',
      'PageDown',
      'PageUp',
      'ArrowDown',
      'ArrowUp',
      'Home',
      'End',
      ' ',
    ].includes(event.key)
  ) {
    pendingScroll = false;
    pendingRestore = undefined;
    navigationGeneration++;
  }
});
for (const event of ['wheel', 'touchmove'])
  addEventListener(
    event,
    () => {
      pendingScroll = false;
      pendingRestore = undefined;
      navigationGeneration++;
    },
    { passive: true },
  );
addEventListener(
  'scroll',
  () => {
    if (pendingScroll && state.kind === 'loading') {
      pendingScroll = false;
      navigationGeneration++;
    }
    // Rendering a ready view can itself move the viewport through scroll anchoring.
    // Pointer/wheel/touch/key intent cancels navigation above; do not mistake
    // ready-layout anchoring for user input before the scheduled target scroll.
    // A loading layout can also clamp a pending history restoration.
    if (state.kind === 'ready') savePosition();
  },
  { passive: true },
);
void loader.load(route.scenario);
