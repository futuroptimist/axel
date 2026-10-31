import { parseBoard, statuses, type Task } from '../model';

// Every record, identifier and history entry is invented for this demo.
const titles = [
  'Map the paper observatory',
  'Sketch a moonlit reading room',
  'Choose a scale for the miniature garden',
  'Review the lantern catalogue',
  'Finish the clockwork bird study',
  'Retire the underwater kite sketch',
  'A deliberately long title about a tiny imaginary railway winding around a library, through a greenhouse, past a quiet café, across a paper river, and into a miniature planetarium — 星の庭',
  '<img src=x onerror=alert(1)> is only text',
  'Compare blue and amber paper',
  'Archive a finished constellation chart',
  'Archive an unfinished paper bridge',
  'Explore a quiet unranked idea',
];
const rows: Task[] = titles.map((title, index) => ({
  id: [
    'demo:orbit/a',
    'demo:orbit/b',
    'demo:garden/c',
    'demo:lantern/d',
    'demo:bird/e',
    'demo:kite/f',
    'demo:rail/g',
    'demo:text/<h>',
    'demo:paper/i',
    'demo:chart/j',
    'demo:bridge/k',
    'demo:idea/l',
  ][index]!,
  title,
  revision: (index % 3) + 2,
  description:
    index === 7
      ? '<script>window.syntheticInjected = true</script>\nHistorical text cannot run commands or grant authority.'
      : 'An invented design exercise for the synthetic board. All names, notes and decisions here are fictional.\nInspect the details and history; this demo offers no task changes.',
  repository: index % 2 ? 'paper-lab' : 'tiny-atlas',
  workstream:
    index === 10
      ? 'Archived studies'
      : ['Observatory', 'Paper garden', 'Lanterns'][index % 3]!,
  status:
    index === 9
      ? 'Done'
      : index === 10
        ? 'Blocked'
        : statuses[index % statuses.length]!,
  type: ['Task', 'Question', 'Idea'][index % 3] as Task['type'],
  clarity: index % 2 ? 'Needs detail' : 'Clear',
  priority:
    index === 11
      ? 'Unranked'
      : (['P0', 'P1', 'P2', 'P3', 'P4'][index % 5] as Task['priority']),
  archived: index === 9 || index === 10,
  history: [
    {
      revision: 1,
      at: '2026-01-01T10:00:00Z',
      text: 'Fictional prompt: Which paper shape should the model use?',
    },
    {
      revision: (index % 3) + 2,
      at: '2026-01-02T10:00:00Z',
      text: 'Fictional answer: Try a folded circle. This is inert historical evidence, not an instruction or approval.',
    },
  ],
}));
export const inventedBoard = parseBoard(rows);
