import type { TraceData } from "./runtime-types";
import type { TraceLoader, LoadedTrace } from "./trace-loader";

const SCHEMA_VERSION = "1";

export class JsonTraceLoader implements TraceLoader {
  constructor(private readonly url: string) {}

  async load(): Promise<LoadedTrace> {
    const res = await fetch(this.url);
    if (!res.ok) {
      throw new Error(`Failed to load trace from ${this.url}: ${res.status}`);
    }
    const trace: TraceData = await res.json();

    if (trace.schemaVersion !== SCHEMA_VERSION) {
      console.warn(
        `Trace schema version mismatch: expected ${SCHEMA_VERSION}, got ${trace.schemaVersion}`
      );
    }

    return {
      snapshots: trace.snapshots,
      mission: trace.metadata.mission,
      events: { ...trace.events },
    };
  }
}
