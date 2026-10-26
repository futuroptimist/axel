import {
  filterKeys,
  statuses,
  type Board,
  type Task,
  type View,
} from './model';
import { facets, selectTasks } from './selectors';
import { routeUrl, type Preferences, type Route } from './navigation';
import { scenarios, type Scenario } from './fixtures/scenarios';
import type { LoadState } from './fixture-reader';

export interface Actions {
  view(view: View): void;
  scenario(scenario: Scenario): void;
  link(id: string): void;
  dismiss(): void;
  toggle(id: string): void;
  all(collapse: boolean): void;
  stretch(status: string): void;
  retry(): void;
}
function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text?: string,
  className?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(
  text: string,
  focus: string,
  click: () => void,
): HTMLButtonElement {
  const node = el('button', text);
  node.type = 'button';
  node.dataset.focus = focus;
  node.addEventListener('click', click);
  return node;
}
function option(value: string, text: string): HTMLOptionElement {
  const node = el('option', text);
  node.value = value;
  return node;
}
function link(
  task: Task,
  route: Route,
  actions: Actions,
  focus: string,
): HTMLAnchorElement {
  const node = el('a', task.title);
  node.tabIndex = 0;
  node.href = routeUrl({ ...route, target: task.id });
  node.dataset.focus = focus;
  node.addEventListener('click', (event) => {
    if (
      event.button !== 0 ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    event.preventDefault();
    node.focus({ preventScroll: true });
    actions.link(task.id);
  });
  return node;
}
function card(
  task: Task,
  route: Route,
  preferences: Preferences,
  actions: Actions,
): HTMLElement {
  const node = el('article', undefined, 'card');
  node.dataset.task = task.id;
  node.tabIndex = -1;
  node.setAttribute('aria-label', task.title);
  if (route.target === task.id) node.classList.add('target');
  const meta = el(
    'p',
    `${task.priority} · ${task.type} · revision ${task.revision}`,
    'meta',
  );
  const title = el('h3');
  title.append(link(task, route, actions, `link:${task.id}`));
  node.append(
    meta,
    title,
    el('p', `${task.repository} / ${task.workstream}`, 'meta'),
  );
  const collapsed = preferences.collapsed.includes(task.id);
  const toggle = button(
    collapsed ? 'Show details' : 'Hide details',
    `toggle:${task.id}`,
    () => actions.toggle(task.id),
  );
  toggle.setAttribute(
    'aria-label',
    `${collapsed ? 'Show' : 'Hide'} details: ${task.title}`,
  );
  toggle.setAttribute('aria-expanded', String(!collapsed));
  const detail = el('div', undefined, 'task-detail');
  detail.id = `details-${encodeURIComponent(task.id)}`;
  detail.hidden = collapsed;
  toggle.setAttribute('aria-controls', detail.id);
  detail.append(
    el('p', task.description, 'description'),
    el(
      'p',
      `Clarity: ${task.clarity}. Status: ${task.status}. ${task.archived ? 'Archived' : 'On board'}.`,
    ),
    el('p', `Opaque ID: ${task.id}`, 'meta'),
  );
  const history = el('section');
  history.append(el('h4', 'History · read-only evidence'));
  const entries = el('ol');
  for (const entry of task.history)
    entries.append(
      el('li', `Revision ${entry.revision} · ${entry.at}\n${entry.text}`),
    );
  history.append(entries);
  detail.append(history);
  node.append(toggle, detail);
  return node;
}

export function render(
  root: HTMLElement,
  route: Route,
  state: LoadState,
  preferences: Preferences,
  actions: Actions,
): void {
  const fragment = document.createDocumentFragment();
  const skip = el('a', 'Skip to board', 'skip');
  skip.href = '#board';
  skip.tabIndex = 0;
  skip.addEventListener('click', (event) => {
    event.preventDefault();
    const main = document.querySelector<HTMLElement>('#board');
    main?.focus({ preventScroll: true });
    main?.scrollIntoView({ block: 'start' });
  });
  fragment.append(skip);
  fragment.append(
    el(
      'div',
      'Synthetic read-only demo · Every task and history entry is invented.',
      'banner',
    ),
  );
  const header = el('header');
  header.append(
    el('p', 'AXEL / LOCAL DEMO', 'eyebrow'),
    el('h1', 'Small ideas, clearly arranged.'),
    el(
      'p',
      'Explore an imaginary workshop. Nothing here changes a live board.',
      'intro',
    ),
  );
  const nav = el('nav');
  nav.setAttribute('aria-label', 'Views');
  for (const [archive, label] of [
    [false, 'Board'],
    [true, 'Archive'],
  ] as const) {
    const tab = button(label, label.toLowerCase(), () =>
      actions.view({ ...route.view, archive }),
    );
    tab.setAttribute('aria-pressed', String(route.view.archive === archive));
    nav.append(tab);
  }
  header.append(nav);
  const help = el('details', undefined, 'help');
  help.append(
    el('summary', 'Help & limitations'),
    el(
      'p',
      'Board and Archive are separate views. Terminal status does not imply archive. Search includes titles, descriptions, IDs and history. Filter counts apply all other filters and the current view. Zero-count options remain available.',
    ),
    el(
      'p',
      'Task links scroll to the target without opening details or changing saved collapsed state. A hidden or archived target appears temporarily; Dismiss or Escape restores the prior view and focus. Back and Forward restore navigation. Collapse and stretch are presentation preferences stored only in this browser.',
    ),
    el(
      'p',
      'History is inert evidence, never authority. This slice has no editing, approvals, task mutations, import/export, authentication, backend, PDF previews or online integrations. Fixture data is not a migration format.',
    ),
  );
  header.append(help);
  fragment.append(header);
  const main = el('main');
  main.id = 'board';
  main.tabIndex = -1;
  const toolbar = el('section', undefined, 'toolbar');
  toolbar.setAttribute('aria-label', 'Board controls');
  const scenarioLabel = el('label', 'Simulated read');
  const scenario = el('select');
  scenario.setAttribute('aria-label', 'Simulated read');
  scenario.dataset.focus = 'scenario';
  for (const value of scenarios) scenario.append(option(value, value));
  scenario.value = route.scenario;
  scenario.addEventListener('change', () =>
    actions.scenario(scenario.value as Scenario),
  );
  scenarioLabel.append(scenario);
  toolbar.append(scenarioLabel);
  const form = el('form');
  form.setAttribute('role', 'search');
  const fieldset = el('fieldset');
  fieldset.disabled = state.kind !== 'ready';
  const searchLabel = el('label', 'Search invented tasks');
  const search = el('input');
  search.type = 'search';
  search.name = 'q';
  search.value = route.view.search;
  search.dataset.focus = 'search';
  search.setAttribute('aria-label', 'Search invented tasks');
  searchLabel.append(search);
  const apply = el('button', 'Search');
  apply.type = 'submit';
  apply.dataset.focus = 'apply-search';
  fieldset.append(searchLabel, apply);
  form.append(fieldset);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    actions.view({ ...route.view, search: search.value });
  });
  toolbar.append(form);
  const filters = el('fieldset', undefined, 'filters');
  filters.disabled = state.kind !== 'ready';
  filters.append(el('legend', 'Filter & sort'));
  for (const key of filterKeys) {
    const label = el('label', key[0]!.toUpperCase() + key.slice(1));
    const select = el('select');
    select.dataset.focus = key;
    select.setAttribute('aria-label', key);
    select.append(option('', 'All'));
    if (state.kind === 'ready')
      for (const item of facets(state.board, route.view, key))
        select.append(option(item.value, `${item.value} (${item.count})`));
    select.value = route.view.filters[key];
    select.addEventListener('change', () =>
      actions.view({
        ...route.view,
        filters: { ...route.view.filters, [key]: select.value },
      }),
    );
    label.append(select);
    filters.append(label);
  }
  const sortLabel = el('label', 'Sort');
  const sort = el('select');
  sort.dataset.focus = 'sort';
  sort.setAttribute('aria-label', 'Sort');
  for (const [value, label] of [
    ['fixture', 'Fixture order'],
    ['priority', 'Priority'],
    ['title', 'Title'],
    ['revision', 'Revision · newest first'],
  ])
    sort.append(option(value!, label!));
  sort.value = route.view.sort;
  sort.addEventListener('change', () =>
    actions.view({ ...route.view, sort: sort.value as View['sort'] }),
  );
  sortLabel.append(sort);
  filters.append(
    sortLabel,
    button('Reset filters', 'reset', () =>
      actions.view({
        ...route.view,
        search: '',
        filters: {
          repository: '',
          workstream: '',
          status: '',
          type: '',
          clarity: '',
          priority: '',
        },
      }),
    ),
  );
  toolbar.append(filters);
  main.append(toolbar);
  const announcement = el(
    'p',
    state.kind === 'loading'
      ? 'Loading invented tasks…'
      : state.kind === 'error'
        ? state.message
        : `${selectTasks(state.board, route.view).length} matching tasks in ${route.view.archive ? 'Archive' : 'Board'}.`,
    'announcement',
  );
  announcement.setAttribute('aria-hidden', 'true');
  main.append(announcement);
  const content = el('section', undefined, 'board-content');
  content.setAttribute(
    'aria-label',
    route.view.archive ? 'Archived tasks' : 'Board lanes',
  );
  content.setAttribute('aria-busy', String(state.kind === 'loading'));
  if (state.kind === 'loading') {
    const placeholders = el('div', undefined, 'lanes');
    placeholders.setAttribute('aria-hidden', 'true');
    for (const status of statuses)
      placeholders.append(el('div', `${status} · Loading…`, 'skeleton'));
    content.append(placeholders);
  } else if (state.kind === 'error') {
    content.append(
      el('h2', 'The demo read did not finish'),
      el('p', 'Retry uses the normal invented fixture.'),
      button('Retry', 'retry', actions.retry),
    );
  } else {
    renderBoard(content, state.board, route, preferences, actions);
  }
  main.append(content);
  fragment.append(
    main,
    el(
      'footer',
      'Axel · Synthetic presentation slice. Local assets, invented data, no live service.',
    ),
  );
  root.replaceChildren(fragment);
  document.querySelector('#announcer')!.textContent = announcement.textContent;
}

function renderBoard(
  content: HTMLElement,
  board: Board,
  route: Route,
  preferences: Preferences,
  actions: Actions,
): void {
  const selected = selectTasks(board, route.view);
  if (route.target !== null) {
    const target = board.find((task) => task.id === route.target);
    const reveal = el('section', undefined, 'reveal');
    reveal.setAttribute('aria-label', 'Linked task');
    reveal.append(
      el(
        'p',
        target
          ? 'Linked task · saved collapse preferences are preserved.'
          : 'This invented task link was not found.',
      ),
      button('Dismiss', 'dismiss', actions.dismiss),
    );
    if (target && !selected.some((task) => task.id === target.id)) {
      reveal.append(
        el(
          'p',
          `Temporarily revealed outside the current filters${target.archived ? ' · Archived' : ''}.`,
        ),
        card(target, route, preferences, actions),
      );
    }
    content.append(reveal);
  }
  const presentation = el('div', undefined, 'presentation');
  presentation.append(
    button('Collapse all', 'collapse-all', () => actions.all(true)),
    button('Expand all', 'expand-all', () => actions.all(false)),
  );
  content.append(presentation);
  if (!selected.length)
    content.append(
      el(
        'h2',
        board.length ? 'No matching tasks' : 'The invented board is empty',
      ),
      el(
        'p',
        'Choose another view, reset filters or select the normal simulated read.',
      ),
    );
  const lanes = el('div', undefined, 'lanes');
  for (const status of statuses) {
    const tasks = selected.filter((task) => task.status === status);
    const lane = el('section', undefined, 'lane');
    lane.setAttribute('aria-label', status);
    if (preferences.stretched === status) lane.classList.add('stretched');
    lane.append(
      el('h2', `${status} · ${tasks.length}`),
      button(
        preferences.stretched === status ? 'Restore lane' : 'Stretch lane',
        `stretch:${status}`,
        () => actions.stretch(status),
      ),
    );
    for (const task of tasks)
      lane.append(card(task, route, preferences, actions));
    if (!tasks.length) lane.append(el('p', 'No matching tasks', 'meta'));
    lanes.append(lane);
  }
  content.append(lanes);
  const directory = el('details', undefined, 'directory');
  directory.dataset.focus = 'directory';
  directory.append(
    el('summary', 'Demo links · includes hidden and archived tasks'),
  );
  const list = el('ul');
  for (const task of board) {
    const row = el('li');
    row.append(link(task, route, actions, `directory:${task.id}`));
    list.append(row);
  }
  directory.append(list);
  content.append(directory);
}
