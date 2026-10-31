import { expect, it, vi } from 'vitest';
import {
  BoardLoader,
  createFixtureReader,
  type LoadState,
} from '../src/fixture-reader';
import { inventedBoard } from '../src/fixtures/invented-board';
import type { Board } from '../src/model';

it('never publishes an older generation, including stale errors', async () => {
  const pending: {
    resolve(value: Board): void;
    reject(reason: Error): void;
  }[] = [];
  const states: LoadState[] = [];
  const loader = new BoardLoader(
    {
      read: () =>
        new Promise((resolve, reject) => pending.push({ resolve, reject })),
    },
    (state) => states.push(state),
  );
  const old = loader.load('slow');
  const fresh = loader.load('empty');
  pending[1]!.resolve([]);
  await fresh;
  pending[0]!.resolve(inventedBoard);
  await old;
  expect(states).toEqual([
    { kind: 'loading' },
    { kind: 'loading' },
    { kind: 'ready', board: [] },
  ]);
  const fail = loader.load('error');
  const newest = loader.load('normal');
  pending[3]!.resolve(inventedBoard);
  await newest;
  pending[2]!.reject(new Error('old'));
  await fail;
  expect(states.at(-1)).toEqual({ kind: 'ready', board: inventedBoard });
});
it('simulates delayed, failed, empty and successful reads without changing fixtures', async () => {
  vi.useFakeTimers();
  try {
    const before = JSON.stringify(inventedBoard);
    const reader = createFixtureReader();
    const result = reader.read('normal');
    await vi.runAllTimersAsync();
    expect(await result).toEqual(inventedBoard);
    const error = expect(reader.read('error')).rejects.toThrow('simulated');
    await vi.runAllTimersAsync();
    await error;
    const empty = reader.read('empty');
    await vi.runAllTimersAsync();
    expect(await empty).toEqual([]);
    expect(JSON.stringify(inventedBoard)).toBe(before);
  } finally {
    vi.useRealTimers();
  }
});
it('clears previous data during errors and retries', async () => {
  const states: LoadState[] = [];
  let attempts = 0;
  const loader = new BoardLoader(
    {
      read: async () => {
        if (!attempts++) throw new Error('simulated');
        return inventedBoard;
      },
    },
    (state) => states.push(state),
  );
  await loader.load('error');
  await loader.load('normal');
  expect(states.map((state) => state.kind)).toEqual([
    'loading',
    'error',
    'loading',
    'ready',
  ]);
});
