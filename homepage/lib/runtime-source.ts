import type { RuntimeState } from "./runtime-types";

export interface EventInfo {
  readonly name: string;
}

export interface RuntimeSource {
  getState(): Readonly<RuntimeState>;
  subscribe(callback: () => void): () => void;
  loadMission(id: string): void;
  dispatchEvent(name: string): void;
  setStatus(s: RuntimeState["status"]): void;
  availableMissions: readonly { readonly id: string; readonly name: string; readonly desc: string; readonly constraints: readonly string[] }[];
  availableEvents: readonly EventInfo[];
}
