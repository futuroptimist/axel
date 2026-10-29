// A presentation model only: this is not a storage or transfer contract.
export const statuses = [
  'Backlog',
  'In progress',
  'Blocked',
  'Ready for review',
  'Done',
  "Won't Fix",
] as const;
export const types = ['Task', 'Question', 'Idea'] as const;
export const clarities = ['Clear', 'Needs detail'] as const;
export const priorities = ['P0', 'P1', 'P2', 'P3', 'P4', 'Unranked'] as const;
export type Status = (typeof statuses)[number];
export interface HistoryEntry {
  revision: number;
  at: string;
  text: string;
}
export interface Task {
  id: string;
  revision: number;
  title: string;
  description: string;
  repository: string;
  workstream: string;
  status: Status;
  type: (typeof types)[number];
  clarity: (typeof clarities)[number];
  priority: (typeof priorities)[number];
  archived: boolean;
  history: readonly HistoryEntry[];
}
export type Board = readonly Task[];
export const filterKeys = [
  'repository',
  'workstream',
  'status',
  'type',
  'clarity',
  'priority',
] as const;
export type FilterKey = (typeof filterKeys)[number];
export type Filters = Record<FilterKey, string>;
export type Sort = 'fixture' | 'priority' | 'title' | 'revision';
export interface View {
  archive: boolean;
  search: string;
  filters: Filters;
  sort: Sort;
}
export function defaultView(): View {
  return {
    archive: false,
    search: '',
    filters: {
      repository: '',
      workstream: '',
      status: '',
      type: '',
      clarity: '',
      priority: '',
    },
    sort: 'fixture',
  };
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function string(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}
function revision(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}
function member(values: readonly string[], value: unknown): boolean {
  return typeof value === 'string' && values.includes(value);
}

/** Validate and copy at the reader boundary. Never normalize opaque IDs or evidence. */
export function parseBoard(value: unknown): Board {
  if (!Array.isArray(value) || value.length > 1000)
    throw new Error('Invalid synthetic board');
  const ids = new Set<string>();
  return Object.freeze(
    value.map((row: unknown) => {
      if (
        !object(row) ||
        !['id', 'title', 'description', 'repository', 'workstream'].every(
          (key) => string(row[key]),
        ) ||
        !revision(row.revision) ||
        !member(statuses, row.status) ||
        !member(types, row.type) ||
        !member(clarities, row.clarity) ||
        !member(priorities, row.priority) ||
        typeof row.archived !== 'boolean' ||
        !Array.isArray(row.history) ||
        row.history.length > 1000
      )
        throw new Error('Invalid synthetic task');
      if (ids.has(row.id as string))
        throw new Error('Duplicate synthetic identity');
      ids.add(row.id as string);
      let previous = 0;
      const history = row.history.map((entry: unknown) => {
        if (
          !object(entry) ||
          !revision(entry.revision) ||
          entry.revision <= previous ||
          entry.revision > Number(row.revision) ||
          !string(entry.text) ||
          !string(entry.at) ||
          !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(entry.at) ||
          !Number.isFinite(Date.parse(entry.at))
        ) {
          throw new Error('Invalid synthetic history');
        }
        previous = entry.revision;
        return Object.freeze({
          revision: entry.revision,
          at: entry.at,
          text: entry.text,
        });
      });
      return Object.freeze({
        id: row.id as string,
        revision: row.revision as number,
        title: row.title as string,
        description: row.description as string,
        repository: row.repository as string,
        workstream: row.workstream as string,
        status: row.status as Status,
        type: row.type as Task['type'],
        clarity: row.clarity as Task['clarity'],
        priority: row.priority as Task['priority'],
        archived: row.archived as boolean,
        history: Object.freeze(history),
      });
    }),
  );
}
