import { inventedBoard } from './fixtures/invented-board';
import type { Scenario } from './fixtures/scenarios';
import { parseBoard, type Board } from './model';

export interface BoardReader {
  read(scenario: Scenario): Promise<Board>;
}
export function createFixtureReader(): BoardReader {
  return {
    async read(scenario) {
      await new Promise((resolve) =>
        setTimeout(resolve, scenario === 'slow' ? 1400 : 100),
      );
      if (scenario === 'error')
        throw new Error('The simulated read failed. No service was contacted.');
      return parseBoard(scenario === 'empty' ? [] : inventedBoard);
    },
  };
}
export type LoadState =
  | { kind: 'loading' }
  | { kind: 'ready'; board: Board }
  | { kind: 'error'; message: string };
/** Only the newest request may publish a complete board generation. */
export class BoardLoader {
  private generation = 0;
  constructor(
    private reader: BoardReader,
    private publish: (state: LoadState) => void,
  ) {}
  async load(scenario: Scenario): Promise<void> {
    const generation = ++this.generation;
    this.publish({ kind: 'loading' });
    try {
      const board = await this.reader.read(scenario);
      if (generation === this.generation)
        this.publish({ kind: 'ready', board });
    } catch {
      if (generation === this.generation)
        this.publish({
          kind: 'error',
          message: 'The simulated read failed. No service was contacted.',
        });
    }
  }
}
