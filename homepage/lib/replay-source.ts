import type { RuntimeSource, EventInfo } from "./runtime-source";
import type { RuntimeState, TraceSnapshot } from "./runtime-types";
import type { TraceLoader } from "./trace-loader";

export class ReplayRuntimeSource implements RuntimeSource {
  private snapshots: readonly TraceSnapshot[] = [];
  private index = 0;
  private listeners = new Set<() => void>();
  private timer: ReturnType<typeof setInterval> | null = null;
  private idleState: RuntimeState;
  private tickToSnapshot: Map<number, TraceSnapshot> = new Map();
  private eventTicks: Record<string, number> = {};
  private _paused = false;

  availableMissions: readonly { readonly id: string; readonly name: string; readonly desc: string; readonly constraints: readonly string[] }[] = [];
  availableEvents: readonly EventInfo[] = [];

  constructor(private readonly loader: TraceLoader) {
    this.idleState = this.buildIdleState();
  }

  async init() {
    try {
      const trace = await this.loader.load();

      this.snapshots = trace.snapshots;
      this.availableMissions = [
        {
          id: trace.mission.id,
          name: trace.mission.name,
          desc: trace.mission.desc,
          constraints: trace.mission.constraints,
        },
      ];
      this.availableEvents = Object.entries(trace.events).map(([name]) => ({ name }));

      for (const [name, tick] of Object.entries(trace.events)) {
        this.eventTicks[name] = tick;
      }
      for (const snap of this.snapshots) {
        this.tickToSnapshot.set(snap.tick, snap as unknown as TraceSnapshot);
      }
    } catch {
      this.snapshots = [];
    }
  }

  private buildIdleState(): RuntimeState {
    return {
      tick: 0,
      timestamp: 0,
      status: "idle",
      mission: null,
      moduleDefs: [],
      world: {
        obstacleDistance: 10,
        terrain: "Unknown",
        slope: 0,
        wheelHealth: 100,
        temperature: 20,
        weather: "Clear",
        commsQuality: 1,
        gpsQuality: 1,
        cameraQuality: 1,
        lidarQuality: 1,
      },
      robot: { x: 0, y: 0, heading: 0, battery: 100, cpu: 0, memory: 0, missionProgress: 0, powerState: "Idle" },
      modules: {},
      decision: null,
      eventHistory: [],
      metrics: {},
      runtimeVersion: "0.1.0",
      schemaVersion: "1",
    };
  }

  getState(): RuntimeState {
    if (this.snapshots.length === 0 || this.index >= this.snapshots.length) {
      return this.idleState;
    }
    if (this._paused) {
      return { ...this.snapshots[this.index], status: "paused" } as unknown as RuntimeState;
    }
    return this.snapshots[this.index] as unknown as RuntimeState;
  }

  subscribe(callback: () => void): () => void {
    this.listeners.add(callback);
    return () => { this.listeners.delete(callback); };
  }

  private notify() {
    this.listeners.forEach(fn => fn());
  }

  loadMission(id: string) {
    this.stop();
    this._paused = false;
    const idx = this.snapshots.findIndex(s => s.mission?.id === id);
    this.index = idx >= 0 ? idx : 0;
    this.notify();
  }

  dispatchEvent(name: string) {
    const tick = this.eventTicks[name];
    if (tick === undefined) return;
    const snap = this.tickToSnapshot.get(tick);
    if (!snap) return;
    const idx = this.snapshots.indexOf(snap);
    if (idx >= 0) {
      this.index = idx;
      this.notify();
    }
  }

  setStatus(s: RuntimeState["status"]) {
    if (s === "running") {
      this._paused = false;
      this.start();
    } else {
      this._paused = true;
      this.stop();
    }
    this.notify();
  }

  seek(tick: number) {
    this.stop();
    this._paused = false;
    let idx = this.snapshots.findIndex(s => s.tick >= tick);
    if (idx === -1) idx = this.snapshots.length - 1;
    this.index = Math.max(0, idx);
    this.notify();
  }

  totalTicks(): number {
    return this.snapshots.length;
  }

  private start() {
    if (this.timer) return;
    this.timer = setInterval(() => {
      if (this.index < this.snapshots.length - 1) {
        this.index++;
        this.notify();
      } else {
        this.stop();
      }
    }, 1200);
  }

  private stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}
