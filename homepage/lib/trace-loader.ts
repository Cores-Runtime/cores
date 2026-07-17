import type { TraceSnapshot } from "./runtime-types";

export interface LoadedTrace {
  readonly snapshots: readonly TraceSnapshot[];
  readonly mission: {
    readonly id: string;
    readonly name: string;
    readonly desc: string;
    readonly constraints: readonly string[];
  };
  readonly events: Readonly<Record<string, number>>;
}

export interface TraceLoader {
  load(): Promise<LoadedTrace>;
}
