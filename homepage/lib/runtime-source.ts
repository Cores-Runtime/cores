import type { SimulatorState } from "./runtime-types";

export interface EventInfo {
  readonly name: string;
}

export interface RuntimeSource {
  getState(): Readonly<SimulatorState>;
  subscribe(callback: () => void): () => void;
  loadMission(id: string): void;
  dispatchEvent(name: string): void;
  setStatus(s: SimulatorState["status"]): void;
  seek(tick: number): void;
  totalTicks(): number;
  availableMissions: readonly { readonly id: string; readonly name: string; readonly desc: string; readonly constraints: readonly string[] }[];
  availableEvents: readonly EventInfo[];
}
