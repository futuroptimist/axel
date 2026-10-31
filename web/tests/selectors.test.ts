import { describe, expect, it } from 'vitest';
import { inventedBoard } from '../src/fixtures/invented-board';
import { defaultView, filterKeys, type Task } from '../src/model';
import { facets, selectTasks } from '../src/selectors';

describe('selectors', () => {
  it.each(filterKeys)('filters %s independently', (key) => {
    const task = inventedBoard[0]!;
    const view = defaultView();
    view.filters[key] = task[key];
    const result = selectTasks(inventedBoard, view);
    expect(result.length).toBeGreaterThan(0);
    expect(result.every((row) => row[key] === task[key] && !row.archived)).toBe(
      true,
    );
  });
  it('combines all filters and search without mutating input', () => {
    const before = JSON.stringify(inventedBoard);
    const task = inventedBoard[0]!;
    const view = defaultView();
    for (const key of filterKeys) view.filters[key] = task[key];
    view.search = task.id;
    expect(selectTasks(inventedBoard, view)).toEqual([task]);
    expect(JSON.stringify(inventedBoard)).toBe(before);
  });
  it('separates archive from terminal status and retains zero count vocabulary', () => {
    const view = defaultView();
    expect(
      selectTasks(inventedBoard, view).some((task) => task.status === 'Done'),
    ).toBe(true);
    expect(
      selectTasks(inventedBoard, view).every((task) => !task.archived),
    ).toBe(true);
    expect(facets(inventedBoard, view, 'workstream')).toContainEqual({
      value: 'Archived studies',
      count: 0,
    });
    view.filters.workstream = 'Archived studies';
    expect(selectTasks(inventedBoard, view)).toHaveLength(0);
    view.archive = true;
    expect(selectTasks(inventedBoard, view)).toHaveLength(1);
    expect(selectTasks(inventedBoard, view)[0]?.status).toBe('Blocked');
  });
  it('workstream counts include every other active constraint', () => {
    const view = defaultView();
    view.filters.repository = 'tiny-atlas';
    view.filters.workstream = 'Observatory';
    const counts = facets(inventedBoard, view, 'workstream');
    const allStreams = {
      ...view,
      filters: { ...view.filters, workstream: '' },
    };
    expect(counts.reduce((total, item) => total + item.count, 0)).toBe(
      selectTasks(inventedBoard, allStreams).length,
    );
    expect(counts.find((item) => item.value === 'Observatory')?.count).toBe(
      selectTasks(inventedBoard, view).length,
    );
  });
  it('keeps ties stable and unranked values last', () => {
    const base = inventedBoard[0]!;
    const rows: Task[] = [
      { ...base, id: 'first', priority: 'Unranked' },
      { ...base, id: 'second' },
      { ...base, id: 'third' },
    ];
    const view = defaultView();
    view.sort = 'priority';
    expect(selectTasks(rows, view).map((task) => task.id)).toEqual([
      'second',
      'third',
      'first',
    ]);
    view.sort = 'title';
    expect(selectTasks(rows, view).map((task) => task.id)).toEqual([
      'first',
      'second',
      'third',
    ]);
    view.sort = 'revision';
    expect(selectTasks(rows, view).map((task) => task.id)).toEqual([
      'first',
      'second',
      'third',
    ]);
  });
  it('searches Unicode and literal hostile text, and does not treat queries as markup', () => {
    const view = defaultView();
    view.search = '星の庭';
    expect(selectTasks(inventedBoard, view)).toHaveLength(1);
    view.search = '<script>';
    expect(selectTasks(inventedBoard, view)).toHaveLength(1);
    view.search = 'Fictional prompt';
    expect(selectTasks(inventedBoard, view)).toHaveLength(10);
  });
});
