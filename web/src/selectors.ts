import {
  clarities,
  priorities,
  statuses,
  types,
  filterKeys,
  type Board,
  type FilterKey,
  type Task,
  type View,
} from './model';

function matches(task: Task, view: View, omit?: FilterKey): boolean {
  const query = view.search.trim().toLocaleLowerCase('en');
  return (
    task.archived === view.archive &&
    (!query ||
      [
        task.id,
        task.title,
        task.description,
        ...task.history.map((entry) => entry.text),
      ]
        .join('\n')
        .toLocaleLowerCase('en')
        .includes(query)) &&
    filterKeys.every(
      (key) =>
        key === omit || !view.filters[key] || task[key] === view.filters[key],
    )
  );
}
export function selectTasks(board: Board, view: View): Task[] {
  return board
    .map((task, index) => ({ task, index }))
    .filter(({ task }) => matches(task, view))
    .sort((a, b) => {
      let order = 0;
      if (view.sort === 'priority')
        order =
          priorities.indexOf(a.task.priority) -
          priorities.indexOf(b.task.priority);
      if (view.sort === 'revision') order = b.task.revision - a.task.revision;
      if (view.sort === 'title')
        order =
          a.task.title < b.task.title
            ? -1
            : a.task.title > b.task.title
              ? 1
              : 0;
      return order || a.index - b.index;
    })
    .map(({ task }) => task);
}
/** Facets include the entire fixture vocabulary, even archived-only and zero-count options.
 * Counts apply all other active constraints, omitting only this facet. */
export function facets(
  board: Board,
  view: View,
  key: FilterKey,
): { value: string; count: number }[] {
  const vocabulary: Record<string, readonly string[]> = {
    status: statuses,
    type: types,
    clarity: clarities,
    priority: priorities,
  };
  const values = [
    ...(vocabulary[key] ?? [...new Set(board.map((task) => task[key]))].sort()),
  ];
  if (view.filters[key] && !values.includes(view.filters[key]))
    values.push(view.filters[key]);
  return values.map((value) => ({
    value,
    count: board.filter(
      (task) => task[key] === value && matches(task, view, key),
    ).length,
  }));
}
