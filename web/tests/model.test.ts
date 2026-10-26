import { describe, expect, it } from 'vitest';
import { inventedBoard } from '../src/fixtures/invented-board';
import { parseBoard } from '../src/model';

describe('presentation boundary', () => {
  it('copies without normalizing opaque identity, revisions or history', () => {
    const source = structuredClone(inventedBoard);
    const parsed = parseBoard(source);
    expect(parsed).toEqual(source);
    expect(parsed).not.toBe(source);
    expect(parsed[0]).not.toBe(source[0]);
    expect(Object.isFrozen(parsed[0]?.history)).toBe(true);
    expect(Object.isFrozen(parsed[0])).toBe(true);
  });
  it.each([
    { id: '' },
    { revision: 0 },
    { revision: 1.1 },
    { archived: 'false' },
    { status: 'Deleted' },
    { type: 'Executable' },
    { clarity: 'unknown' },
    { priority: 'P9' },
    { description: null },
    {
      history: [
        { revision: 99, at: '2026-01-01T10:00:00Z', text: 'invalid revision' },
      ],
    },
    { history: [{ revision: 1, at: 'not a date', text: 'invalid date' }] },
  ])('rejects malformed task %j', (patch) => {
    expect(() => parseBoard([{ ...inventedBoard[0], ...patch }])).toThrow();
  });
  it('rejects duplicate identities and unordered history', () => {
    expect(() => parseBoard([inventedBoard[0], inventedBoard[0]])).toThrow(
      'Duplicate',
    );
    expect(() =>
      parseBoard([
        {
          ...inventedBoard[0],
          history: [...inventedBoard[0]!.history].reverse(),
        },
      ]),
    ).toThrow();
    expect(() => parseBoard({ tasks: [] })).toThrow();
    expect(parseBoard([])).toEqual([]);
  });
});
