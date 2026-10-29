import { defaultView, filterKeys, type View } from './model';
import { parseScenario, type Scenario } from './fixtures/scenarios';

export interface Route {
  view: View;
  target: string | null;
  scenario: Scenario;
}
export function readRoute(url: URL): Route {
  const view = defaultView();
  view.archive = url.searchParams.get('view') === 'archive';
  view.search = url.searchParams.get('q') ?? '';
  for (const key of filterKeys)
    view.filters[key] = url.searchParams.get(key) ?? '';
  const sort = url.searchParams.get('sort');
  if (sort === 'priority' || sort === 'title' || sort === 'revision')
    view.sort = sort;
  return {
    view,
    target: url.searchParams.get('task'),
    scenario: parseScenario(url.searchParams.get('scenario')),
  };
}
export function routeUrl(route: Route): string {
  const params = new URLSearchParams();
  if (route.view.archive) params.set('view', 'archive');
  if (route.view.search) params.set('q', route.view.search);
  for (const key of filterKeys)
    if (route.view.filters[key]) params.set(key, route.view.filters[key]);
  if (route.view.sort !== 'fixture') params.set('sort', route.view.sort);
  if (route.scenario !== 'normal') params.set('scenario', route.scenario);
  if (route.target !== null) params.set('task', route.target);
  return params.size ? `?${params.toString()}` : './';
}
export const preferenceKey = 'axel.synthetic-board.presentation.v1';
export interface Preferences {
  collapsed: string[];
  stretched: string | null;
}
export function readPreferences(
  storage: Pick<Storage, 'getItem'>,
): Preferences {
  try {
    const value: unknown = JSON.parse(storage.getItem(preferenceKey) ?? 'null');
    if (
      typeof value === 'object' &&
      value !== null &&
      'collapsed' in value &&
      'stretched' in value &&
      Array.isArray(value.collapsed) &&
      value.collapsed.length <= 1000 &&
      value.collapsed.every((id) => typeof id === 'string') &&
      (typeof value.stretched === 'string' || value.stretched === null)
    )
      return { collapsed: [...value.collapsed], stretched: value.stretched };
  } catch {
    /* Storage may be unavailable; presentation still works. */
  }
  return { collapsed: [], stretched: null };
}
export function savePreferences(
  storage: Pick<Storage, 'setItem'>,
  preferences: Preferences,
): void {
  try {
    storage.setItem(preferenceKey, JSON.stringify(preferences));
  } catch {
    /* Optional persistence. */
  }
}
