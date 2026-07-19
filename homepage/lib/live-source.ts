import type { RuntimeSource, EventInfo } from "./runtime-source";
import type {
  SimulatorState,
  ModuleState,
  WorldState,
  RobotState,
  Decision,
  EventEntry,
} from "./runtime-types";

type RawEvent = {
  event_id: string;
  timestamp: string;
  source: string;
  event_type: string;
  payload: Record<string, unknown>;
};

type RawScores = Record<string, Record<string, number>>;

type RawSchedulerState = {
  policy: string;
  mode: string;
  cycle_count: number;
  selected_modules: string[];
  deferred_modules: string[];
  resource_usage: Record<string, number>;
  constraints_active: string[];
  constraint_violation: boolean;
  decision_time_ms: number;
  scores: RawScores;
  lexicographic_value: Record<string, number> | null;
};

type RawRobotSnapshot = {
  battery_level: number;
  position: Record<string, number>;
  velocity: Record<string, number>;
  flags: Record<string, boolean>;
};

type RawModuleState = {
  name: string;
  status: string;
  priority: number;
  safety_weight: number;
  mission_weight: number;
  urgency_weight: number;
  compute_cost: number;
  time_cost_ms: number;
  energy_cost: number;
  is_safety_critical: boolean;
  is_diagnostic: boolean;
  is_recovery: boolean;
  is_localization: boolean;
};

type RawMissionState = {
  mission_id: string;
  state: string;
  progress: number;
};

type RawExplainabilityState = {
  module_changes: string[];
  scheduler_rationale: string;
};

type RawEventsSnapshot = {
  cycle_events: RawEvent[];
  obstacles: RawEvent[];
  warnings: RawEvent[];
  recoveries: RawEvent[];
};

type RawRuntimeState = {
  timestamp: string;
  mission: RawMissionState;
  modules: RawModuleState[];
  active_module_names: string[];
  sleeping_module_names: string[];
  suspended_module_names: string[];
  scheduler: RawSchedulerState;
  robot: RawRobotSnapshot;
  events: RawEventsSnapshot;
  explainability: RawExplainabilityState;
};

type ProtocolEnvelope = {
  version: string;
  type: string;
  payload: RawRuntimeState;
};

const DEFAULT_WEBSOCKET_URL = "ws://127.0.0.1:8765";
const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_DELAY_MS = 30000;

export class LiveRuntimeSource implements RuntimeSource {
  private ws: WebSocket | null = null;
  private url: string;
  private listeners = new Set<() => void>();

  private _state: SimulatorState;
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _reconnectAttempt = 0;
  private _destroyed = false;
  private _eventHistory: EventEntry[] = [];

  availableMissions: readonly { readonly id: string; readonly name: string; readonly desc: string; readonly constraints: readonly string[] }[] = [];
  availableEvents: readonly EventInfo[] = [];

  constructor(url?: string) {
    this.url = url ?? DEFAULT_WEBSOCKET_URL;
    this._state = this.buildIdleState();
  }

  async init(): Promise<void> {
    this.connect();
  }

  private buildIdleState(): SimulatorState {
    return {
      tick: 0,
      timestamp: 0,
      status: "running",
      mission: null,
      moduleDefs: [
        { id: "safety_monitor", name: "Safety Monitor", priority: 0, cpuCost: 0, deps: [], purpose: "Monitor system safety" },
        { id: "battery_monitor", name: "Battery Monitor", priority: 0, cpuCost: 0, deps: [], purpose: "Monitor battery levels" },
        { id: "navigator", name: "Navigator", priority: 0, cpuCost: 0, deps: ["localization"], purpose: "Path planning" },
        { id: "collision_avoidance", name: "Collision Avoidance", priority: 0, cpuCost: 0, deps: [], purpose: "Avoid obstacles" },
        { id: "localization", name: "Localization", priority: 0, cpuCost: 0, deps: [], purpose: "Localize robot position" },
        { id: "mapper", name: "Mapper", priority: 0, cpuCost: 0, deps: ["localization"], purpose: "Build environment map" },
        { id: "explorer", name: "Explorer", priority: 0, cpuCost: 0, deps: ["navigator"], purpose: "Explore terrain" },
        { id: "diagnostics", name: "Diagnostics", priority: 0, cpuCost: 0, deps: [], purpose: "Run diagnostics" },
        { id: "recovery", name: "Recovery", priority: 0, cpuCost: 0, deps: ["diagnostics"], purpose: "Recover from faults" },
        { id: "logger", name: "Logger", priority: 0, cpuCost: 0, deps: [], purpose: "Log system state" },
      ],
      world: {
        obstacleDistance: 10,
        terrain: "Mars",
        slope: 0,
        wheelHealth: 100,
        temperature: 20,
        weather: "Clear",
        commsQuality: 1,
        gpsQuality: 1,
        cameraQuality: 1,
        lidarQuality: 1,
      },
      robot: { x: 0, y: 0, heading: 0, battery: 100, cpu: 0, memory: 0, missionProgress: 0, powerState: "Nominal" },
      modules: {},
      decision: null,
      eventHistory: [],
      metrics: {},
      runtimeVersion: "0.1.0",
      schemaVersion: "1",
    };
  }

  private connect(): void {
    if (this._destroyed) return;

    try {
      this.ws = new WebSocket(this.url);
    } catch (err) {
      console.error("[LiveRuntimeSource] WebSocket construction failed:", err);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this._reconnectAttempt = 0;
    };

    this.ws.onmessage = (msg: MessageEvent) => {
      try {
        const envelope: ProtocolEnvelope = JSON.parse(msg.data);
        if (envelope.type !== "runtime_snapshot") return;
        this.applySnapshot(envelope.payload);
      } catch (err) {
        console.error("[LiveRuntimeSource] Failed to parse snapshot:", err);
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (!this._destroyed) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
    };
  }

  private scheduleReconnect(): void {
    if (this._destroyed) return;
    if (this._reconnectTimer) return;

    const delay = Math.min(
      RECONNECT_DELAY_MS * Math.pow(2, this._reconnectAttempt),
      MAX_RECONNECT_DELAY_MS,
    );
    this._reconnectAttempt++;

    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private applySnapshot(raw: RawRuntimeState): void {
    const moduleDefs = this._state.moduleDefs;
    const modules: Record<string, ModuleState> = {};
    let tick = this._state.tick + 1;

    for (const m of raw.modules) {
      const isActive = raw.active_module_names.includes(m.name);
      const isSuspended = raw.suspended_module_names.includes(m.name);
      let status: ModuleState["status"] = "sleeping";
      if (isActive) status = "running";
      else if (isSuspended) status = "suspended";

      modules[m.name] = {
        status,
        reason: "",
        cpu: m.compute_cost * 100,
        task: `${m.name} task`,
        lastActivation: tick,
        wakeCount: isActive ? 1 : 0,
        totalRuntime: m.time_cost_ms,
        recentDecisions: [],
      };
    }

    const selected = raw.scheduler.selected_modules;
    const deferred = raw.scheduler.deferred_modules;

    let roboX = raw.robot.position.x ?? 0;
    let roboY = raw.robot.position.y ?? 0;
    const missionProgress = raw.mission.progress * 100;
    const heading = raw.robot.position.theta ?? 0;

    const robot: RobotState = {
      x: roboX,
      y: roboY,
      heading,
      battery: raw.robot.battery_level * 100,
      cpu: 50,
      memory: 40,
      missionProgress,
      powerState: raw.scheduler.mode === "low_power" ? "Low Power" : "Nominal",
    };

    const decision: Decision | null = selected.length > 0 || deferred.length > 0 ? {
      tick,
      reason: raw.explainability.scheduler_rationale,
      wake: selected,
      sleep: [],
      suspend: deferred,
      priority: raw.scheduler.policy || "default",
      hierarchy: raw.scheduler.constraints_active.map(c => `constraint:${c}`),
      decisionTimeMs: raw.scheduler.decision_time_ms,
    } : null;

    const hasObstacle = raw.robot.flags?.obstacle_detected ?? false;
    const world: WorldState = {
      obstacleDistance: hasObstacle ? 0.3 : 10,
      terrain: "Mars",
      slope: 0,
      wheelHealth: raw.scheduler.mode === "emergency" ? 60 : 100,
      temperature: 20,
      weather: raw.scheduler.mode === "low_power" ? "Dust Storm" : "Clear",
      commsQuality: 1,
      gpsQuality: 1,
      cameraQuality: raw.robot.flags?.sensor_failure ? 0.3 : 1,
      lidarQuality: raw.robot.flags?.sensor_failure ? 0.2 : 1,
    };

    const eventsForTick: EventEntry[] = [];
    for (const ev of raw.events.cycle_events) {
      const entry: EventEntry = {
        tick,
        time: tick,
        event: ev.source + ": " + (ev.payload?.message ?? ev.event_type),
        type: ev.event_type === "system_emergency" ? "warning"
          : ev.event_type === "module_failed" ? "warning"
          : ev.event_type === "diagnostic" ? "info"
          : "info",
      };
      eventsForTick.push(entry);
    }

    const allEvents = [...this._eventHistory, ...eventsForTick];
    const maxEvents = 80;
    const trimmedEvents = allEvents.length > maxEvents
      ? allEvents.slice(allEvents.length - maxEvents)
      : allEvents;
    this._eventHistory = trimmedEvents;

    const metrics: Record<string, number[]> = {};
    metrics.battery = [raw.robot.battery_level * 100];
    metrics.cpu = [50];
    metrics.memory = [40];
    metrics.latency = [raw.scheduler.decision_time_ms];
    metrics.utility = [raw.mission.progress * 100];
    metrics.safety = [raw.scheduler.mode === "emergency" ? 0 : 100];
    metrics.headroom = raw.scheduler.resource_usage?.energy !== undefined
      ? [Math.max(0, 100 - raw.scheduler.resource_usage.energy * 100)]
      : [100];
    metrics.events = [raw.events.cycle_events.length];

    this._state = {
      tick,
      timestamp: Date.now(),
      status: "running",
      mission: {
        id: raw.mission.mission_id || "live-mission",
        name: "Live Mission",
        desc: "Real-time CORES runtime execution",
        constraints: raw.scheduler.constraints_active,
      },
      moduleDefs,
      world,
      robot,
      modules,
      decision,
      eventHistory: this._eventHistory,
      metrics,
      runtimeVersion: "0.1.0",
      schemaVersion: "1",
    };

    this.notify();
  }

  getState(): SimulatorState {
    return this._state;
  }

  subscribe(callback: () => void): () => void {
    this.listeners.add(callback);
    return () => { this.listeners.delete(callback); };
  }

  private notify(): void {
    this.listeners.forEach(fn => fn());
  }

  loadMission(id: string): void {
  }

  dispatchEvent(name: string): void {
  }

  setStatus(s: SimulatorState["status"]): void {
  }

  seek(tick: number): void {
  }

  totalTicks(): number {
    return 1;
  }

  destroy(): void {
    this._destroyed = true;
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
    this._eventHistory = [];
  }
}
