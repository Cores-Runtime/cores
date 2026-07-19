export interface ModuleDef {
  readonly id: string;
  readonly name: string;
  readonly priority: number;
  readonly cpuCost: number;
  readonly deps: readonly string[];
  readonly purpose: string;
}

export type ModuleStatus = "sleeping" | "thinking" | "running" | "suspended";

export interface ModuleState {
  readonly status: ModuleStatus;
  readonly reason: string;
  readonly cpu: number;
  readonly task: string;
  readonly lastActivation: number;
  readonly wakeCount: number;
  readonly totalRuntime: number;
  readonly recentDecisions: readonly string[];
}

export interface WorldState {
  readonly obstacleDistance: number;
  readonly terrain: string;
  readonly slope: number;
  readonly wheelHealth: number;
  readonly temperature: number;
  readonly weather: string;
  readonly commsQuality: number;
  readonly gpsQuality: number;
  readonly cameraQuality: number;
  readonly lidarQuality: number;
}

export interface RobotState {
  readonly x: number;
  readonly y: number;
  readonly heading: number;
  readonly battery: number;
  readonly cpu: number;
  readonly memory: number;
  readonly missionProgress: number;
  readonly powerState: string;
}

export interface Decision {
  readonly tick: number;
  readonly reason: string;
  readonly wake: readonly string[];
  readonly sleep: readonly string[];
  readonly suspend: readonly string[];
  readonly priority: string;
  readonly hierarchy: readonly string[];
  readonly decisionTimeMs: number;
}

export interface EventEntry {
  readonly tick: number;
  readonly time: number;
  readonly event: string;
  readonly type: "info" | "warning" | "decision" | "module" | "success" | "thinking";
}

export interface MissionInfo {
  readonly id: string;
  readonly name: string;
  readonly desc: string;
  readonly constraints: readonly string[];
}

export interface TraceMetadata {
  readonly mission: {
    readonly id: string;
    readonly name: string;
    readonly desc: string;
    readonly constraints: readonly string[];
  };
  readonly robot: {
    readonly platform: string;
    readonly sensors: readonly string[];
    readonly actuators: readonly string[];
  };
  readonly environment: {
    readonly type: string;
    readonly hazards: readonly string[];
    readonly lighting: string;
  };
  readonly scenario: {
    readonly id: string;
    readonly category: string;
    readonly difficulty: string;
  };
}

export interface SimulatorState {
  readonly tick: number;
  readonly timestamp: number;
  readonly status: "idle" | "running" | "paused";
  readonly mission: MissionInfo | null;
  readonly moduleDefs: readonly ModuleDef[];
  readonly world: WorldState;
  readonly robot: RobotState;
  readonly modules: Readonly<Record<string, ModuleState>>;
  readonly decision: Decision | null;
  readonly eventHistory: readonly EventEntry[];
  readonly metrics: Readonly<Record<string, readonly number[]>>;
  readonly runtimeVersion: string;
  readonly schemaVersion: string;
}

export interface TraceSnapshot {
  readonly tick: number;
  readonly timestamp: number;
  readonly status: "idle" | "running" | "paused";
  readonly mission: MissionInfo | null;
  readonly moduleDefs: readonly ModuleDef[];
  readonly world: WorldState;
  readonly robot: RobotState;
  readonly modules: Readonly<Record<string, ModuleState>>;
  readonly decision: Decision | null;
  readonly eventHistory: readonly EventEntry[];
  readonly metrics: Readonly<Record<string, readonly number[]>>;
  readonly runtimeVersion: string;
  readonly schemaVersion: string;
}

export interface TraceData {
  readonly version: string;
  readonly schemaVersion: string;
  readonly metadata: TraceMetadata;
  readonly events: Readonly<Record<string, number>>;
  readonly snapshots: readonly TraceSnapshot[];
}
