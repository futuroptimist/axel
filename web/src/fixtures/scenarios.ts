export const scenarios = ['normal', 'slow', 'error', 'empty'] as const;
export type Scenario = (typeof scenarios)[number];
export function parseScenario(value: string | null): Scenario {
  return scenarios.includes(value as Scenario) ? (value as Scenario) : 'normal';
}
