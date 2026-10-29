import { expect, it } from 'vitest';
import { inventedBoard } from '../src/fixtures/invented-board';
import { statuses } from '../src/model';
import {
  preferenceKey,
  readPreferences,
  readRoute,
  routeUrl,
  savePreferences,
} from '../src/navigation';

it('covers all six statuses, separate archive, long Unicode and hostile text', () => {
  expect(new Set(inventedBoard.map((task) => task.status))).toEqual(
    new Set(statuses),
  );
  expect(inventedBoard.every((task) => task.id.startsWith('demo:'))).toBe(true);
  expect(inventedBoard.some((task) => task.archived)).toBe(true);
  expect(inventedBoard.some((task) => task.title.length > 150)).toBe(true);
  expect(
    inventedBoard.some((task) => task.description.includes('<script>')),
  ).toBe(true);
});
it('round trips opaque IDs and filter values through permanent links', () => {
  const route = readRoute(
    new URL(
      'http://localhost/?task=demo%3Atext%2F%3Ch%3E&view=archive&workstream=Paper%20garden&q=%E6%98%9F&sort=priority',
    ),
  );
  expect(readRoute(new URL(routeUrl(route), 'http://localhost'))).toEqual(
    route,
  );
});
it('stores only bounded presentation preferences and tolerates unavailable storage', () => {
  const values = new Map<string, string>();
  const storage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    },
  };
  savePreferences(storage, { collapsed: ['demo:orbit/a'], stretched: null });
  expect([...values.keys()]).toEqual([preferenceKey]);
  expect(Object.keys(JSON.parse(values.get(preferenceKey)!))).toEqual([
    'collapsed',
    'stretched',
  ]);
  expect(readPreferences(storage)).toEqual({
    collapsed: ['demo:orbit/a'],
    stretched: null,
  });
  expect(readPreferences({ getItem: () => '{bad' })).toEqual({
    collapsed: [],
    stretched: null,
  });
  expect(() =>
    savePreferences(
      {
        setItem: () => {
          throw new Error('Unavailable');
        },
      },
      { collapsed: [], stretched: null },
    ),
  ).not.toThrow();
});
