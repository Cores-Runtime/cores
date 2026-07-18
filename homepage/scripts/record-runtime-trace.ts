import * as fs from "fs";
import * as path from "path";
import type { TraceData, TraceSnapshot, WorldState, RobotState, Decision, ModuleState, ModuleDef, EventEntry } from "../lib/runtime-types";

type Mutable<T> = { -readonly [P in keyof T]: T[P] };

const MODULE_DEFS: ModuleDef[] = [
  { id: "mission-manager", name: "Mission Manager", priority: 1, cpuCost: 12, deps: [], purpose: "Mission-level decision making." },
  { id: "perception-engine", name: "Perception Engine", priority: 2, cpuCost: 18, deps: ["mission-manager"], purpose: "Analyzes terrain and samples." },
  { id: "planning-engine", name: "Planning Engine", priority: 3, cpuCost: 24, deps: ["perception-engine"], purpose: "Trajectory optimization." },
  { id: "state-estimator", name: "State Estimator", priority: 7, cpuCost: 8, deps: ["planning-engine"], purpose: "Thermal and power modeling." },
  { id: "navigation-controller", name: "Navigation Controller", priority: 1, cpuCost: 6, deps: ["mission-manager", "state-estimator"], purpose: "Obstacle avoidance." },
  { id: "motion-controller", name: "Motion Controller", priority: 4, cpuCost: 14, deps: ["navigation-controller", "planning-engine"], purpose: "Path execution." },
  { id: "safety-supervisor", name: "Safety Supervisor", priority: 9, cpuCost: 2, deps: ["mission-manager"], purpose: "Mission control interface." },
  { id: "telemetry-logger", name: "Telemetry / Logger", priority: 5, cpuCost: 2, deps: [], purpose: "Mission logging." },
  { id: "policy-engine", name: "Policy Engine", priority: 8, cpuCost: 1, deps: ["mission-manager", "telemetry-logger"], purpose: "Ethical validation." },
];

const MISSION = {
  id: "mars_rover",
  name: "Mars Exploration",
  desc: "Navigate rocky terrain to reach a sample site 500m away.",
  constraints: ["Low power budget", "21-min comms delay", "Thermal cycling"],
};

const METADATA = {
  mission: { id: "mars_rover", name: "Mars Exploration", desc: "Navigate rocky terrain to reach a sample site 500m away.", constraints: ["Low power budget", "21-min comms delay", "Thermal cycling"] },
  robot: { platform: "Rover-X2", sensors: ["camera", "lidar", "gps", "imu", "thermal"], actuators: ["wheel", "arm", "antenna"], environment: { type: "Martian surface", hazards: ["rocks", "dust storms", "extreme cold", "radiation"], lighting: "Variable" }, scenario: { id: "exploration_01", category: "planetary", difficulty: "hard" } },
  environment: { type: "Martian surface", hazards: ["rocks", "dust storms", "extreme cold", "radiation"], lighting: "Variable" },
  scenario: { id: "exploration_01", category: "planetary", difficulty: "hard" },
};

function buildModules(overrides: Record<string, Partial<ModuleState>> = {}): Record<string, Mutable<ModuleState>> {
  const base: Record<string, ModuleState> = {};
  for (const m of MODULE_DEFS) {
    const active = m.id === "mission-manager" || m.id === "telemetry-logger";
    base[m.id] = {
      status: active ? "running" : "sleeping",
      reason: active ? "Core" : "Awaiting trigger",
      cpu: 0,
      task: "Standby",
      lastActivation: 0,
      wakeCount: 0,
      totalRuntime: 0,
      recentDecisions: [],
      ...(overrides[m.id] || {}),
    };
  }
  return base;
}

function cloneMods(mods: Record<string, Mutable<ModuleState>>): Record<string, Mutable<ModuleState>> {
  const out: Record<string, ModuleState> = {};
  for (const [k, v] of Object.entries(mods)) out[k] = { ...v, recentDecisions: [...v.recentDecisions] };
  return out;
}

function buildSnap(
  tick: number,
  world: Mutable<WorldState>,
  robot: Mutable<RobotState>,
  modules: Record<string, Mutable<ModuleState>>,
  decision: Decision | null,
  eventHistory: EventEntry[],
  metrics: Record<string, number[]>,
): TraceSnapshot {
  return {
    tick,
    timestamp: tick * 300,
    status: "running",
    mission: MISSION,
    moduleDefs: MODULE_DEFS,
    world: { ...world },
    robot: { ...robot },
    modules: cloneMods(modules),
    decision: decision ? { ...decision, hierarchy: [...decision.hierarchy], wake: [...decision.wake], sleep: [...decision.sleep], suspend: [...decision.suspend] } : null,
    eventHistory: eventHistory.map(e => ({ ...e })),
    metrics: Object.fromEntries(Object.entries(metrics).map(([k, arr]) => [k, [...arr]])),
    runtimeVersion: "0.1.0",
    schemaVersion: "1",
  };
}

function fillSnaps(
  startTick: number, count: number,
  world: Mutable<WorldState>, robot: Mutable<RobotState>, modules: Record<string, Mutable<ModuleState>>,
  decision: Decision | null,
  eventHistory: EventEntry[],
  metrics: Record<string, number[]>,
  change: (w: Mutable<WorldState>, r: Mutable<RobotState>, mods: Record<string, Mutable<ModuleState>>, d: Decision | null, t: EventEntry[], m: Record<string, number[]>) => void,
): TraceSnapshot[] {
  const out: TraceSnapshot[] = [];
  const w = { ...world };
  const r = { ...robot };
  const mods = cloneMods(modules);
  const t = eventHistory.map(e => ({ ...e }));
  const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(metrics)) m[k] = [...arr];

  let curD = decision ? { ...decision, hierarchy: [...decision.hierarchy], wake: [...decision.wake], sleep: [...decision.sleep], suspend: [...decision.suspend] } : null;

  for (let i = 0; i < count; i++) {
    const tick = startTick + i;
    change(w, r, mods, curD, t, m);
    out.push(buildSnap(tick, w, r, mods, curD, t, m));
  }
  return out;
}

function initWorld(): Mutable<WorldState> {
  return { obstacleDistance: 12, terrain: "Rocky Gravel", slope: 3, wheelHealth: 100, temperature: -60, weather: "Clear", commsQuality: 0.7, gpsQuality: 0.9, cameraQuality: 0.95, lidarQuality: 0.9 };
}

function initRobot(): Mutable<RobotState> {
  return { x: 0, y: 0, heading: 45, battery: 100, cpu: 15, memory: 35, missionProgress: 2, powerState: "Nominal" };
}

function nominalChange(w: Mutable<WorldState>, r: Mutable<RobotState>, mods: Record<string, Mutable<ModuleState>>, _d: Decision | null, _t: EventEntry[], m: Record<string, number[]>) {
  r.battery = Math.max(0, r.battery - 0.3);
  r.missionProgress = Math.min(100, r.missionProgress + 1.5);
  w.obstacleDistance = Math.max(1, w.obstacleDistance - 0.02);
  r.cpu = 15 + Math.round(Math.random() * 5);
  for (const mod of Object.values(mods)) {
    if (mod.status === "running") { mod.totalRuntime += 1; mod.cpu = Math.round(6 + Math.random() * 8); }
  }
  m.battery.push(Math.round(r.battery * 10) / 10);
  m.cpu.push(r.cpu);
  m.memory.push(Math.round(35 + Math.random() * 5));
  m.latency.push(Math.round((0.5 + Math.random() * 0.3) * 100) / 100);
  m.missionUtility.push(Math.round(r.missionProgress * 10) / 10);
  m.safetyScore.push(Math.round(95 + Math.random() * 3));
  m.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10);
  m.eventsPerSec.push(Math.round(100 + Math.random() * 20));
}

// --- BUILD TRACE ---

const snapshots: TraceSnapshot[] = [];

// Tick 0
{
  const w = initWorld(); const r = initRobot(); const mods = buildModules(); const t: EventEntry[] = [];
  const m: Record<string, number[]> = { battery: [], cpu: [], memory: [], latency: [], missionUtility: [], safetyScore: [], energyHeadroom: [], eventsPerSec: [] };
  t.push({ tick: 0, time: 0, event: "Mission loaded: Mars Exploration", type: "info" });
  t.push({ tick: 0, time: 0, event: "Runtime online", type: "success" });
  m.battery.push(r.battery); m.cpu.push(r.cpu); m.memory.push(r.memory);
  m.latency.push(0.6); m.missionUtility.push(r.missionProgress);
  m.safetyScore.push(95); m.energyHeadroom.push(20); m.eventsPerSec.push(100);
  snapshots.push(buildSnap(0, w, r, mods, null, t, m));
}

// Ticks 1-9
{
  const w = initWorld(); const r = initRobot(); const mods = buildModules();
  r.battery = 100; r.missionProgress = 2;
  const t: EventEntry[] = []; const m: Record<string, number[]> = { battery: [100], cpu: [15], memory: [35], latency: [0.6], missionUtility: [2], safetyScore: [95], energyHeadroom: [20], eventsPerSec: [100] };
  snapshots.push(...fillSnaps(1, 9, w, r, mods, null, t, m, (w2, r2, mods2, _d, _t2, m2) => { nominalChange(w2, r2, mods2, _d, _t2, m2); }));
}

// Tick 10: Rockslide
{
  const last = snapshots[snapshots.length - 1];
  const w = { ...last.world, obstacleDistance: 0.3, terrain: "Rocky Debris", wheelHealth: 85 };
  const r = { ...last.robot };
  const mods = cloneMods(last.modules);
  const t = last.eventHistory.map(e => ({ ...e }));
  const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  t.push({ tick: 10, time: 3000, event: "Rockslide — obstacle at 0.3m", type: "warning" });
  mods["navigation-controller"].status = "running"; mods["navigation-controller"].reason = "Activated: Obstacle avoidance"; mods["navigation-controller"].lastActivation = 10; mods["navigation-controller"].wakeCount = 1; mods["navigation-controller"].task = "Active";
  mods["motion-controller"].status = "suspended"; mods["motion-controller"].reason = "Obstacle at 0.3m";
  mods["perception-engine"].status = "running"; mods["perception-engine"].reason = "Activated: Route replan"; mods["perception-engine"].lastActivation = 10; mods["perception-engine"].wakeCount = 1; mods["perception-engine"].task = "Active";
  mods["planning-engine"].status = "suspended"; mods["planning-engine"].reason = "Obstacle at 0.3m";
  const decision: Decision = { tick: 10, reason: "Obstacle within 0.3m. Navigation Controller activated for avoidance.", wake: ["navigation-controller", "perception-engine"], sleep: [], suspend: ["motion-controller", "planning-engine"], priority: "Safety", hierarchy: ["Safety", "Mission", "Energy", "Memory"], decisionTimeMs: 0.82 };
  r.cpu = 25;
  m.battery.push(Math.round(r.battery * 10) / 10); m.cpu.push(25); m.memory.push(Math.round(38 + Math.random() * 3)); m.latency.push(0.82);
  m.missionUtility.push(Math.round(r.missionProgress * 10) / 10); m.safetyScore.push(80); m.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); m.eventsPerSec.push(Math.round(120 + Math.random() * 20));
  mods["navigation-controller"].cpu = 6; mods["perception-engine"].cpu = 18; mods["motion-controller"].cpu = 0; mods["planning-engine"].cpu = 0;
  snapshots.push(buildSnap(10, w, r, mods, decision, t, m));
}

// Ticks 11-19
{
  const last = snapshots[snapshots.length - 1];
  const t = last.eventHistory.map(e => ({ ...e }));
  const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  snapshots.push(...fillSnaps(11, 9, last.world, last.robot, last.modules, last.decision as Decision, t, m, (w, r, mods, _d, _t, _m2) => {
    r.battery = Math.max(0, r.battery - 0.5); r.missionProgress = Math.min(100, r.missionProgress + 1.0);
    w.obstacleDistance = Math.min(8, w.obstacleDistance + 0.2); r.cpu = 28 + Math.round(Math.random() * 4);
    for (const mod of Object.values(mods)) { if (mod.status === "running") { mod.totalRuntime += 1; mod.cpu = Math.round(6 + Math.random() * 12); } if (mod.status !== "running") mod.cpu = 0; }
    mods["navigation-controller"].task = "Navigating around obstacle"; mods["navigation-controller"].reason = "Obstacle Avoidance";
    mods["perception-engine"].task = "Recalculating safe route"; mods["perception-engine"].reason = "Route Replan";
    _m2.battery.push(Math.round(r.battery * 10) / 10); _m2.cpu.push(r.cpu); _m2.memory.push(Math.round(40 + Math.random() * 5));
    _m2.latency.push(Math.round((0.7 + Math.random() * 0.3) * 100) / 100); _m2.missionUtility.push(Math.round(r.missionProgress * 10) / 10);
    _m2.safetyScore.push(Math.round(82 + Math.random() * 3)); _m2.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); _m2.eventsPerSec.push(Math.round(130 + Math.random() * 20));
  }));
}

// Tick 20: Obstacle cleared
{
  const last = snapshots[snapshots.length - 1];
  const w = { ...last.world, obstacleDistance: 5.1, terrain: "Rocky Gravel" };
  const r = { ...last.robot }; const mods = cloneMods(last.modules);
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  t.push({ tick: 20, time: 6000, event: "Obstacle cleared. Resuming normal operation.", type: "success" });
  mods["navigation-controller"].status = "sleeping"; mods["navigation-controller"].reason = "Standby"; mods["navigation-controller"].task = "Standby"; mods["navigation-controller"].cpu = 0;
  mods["motion-controller"].status = "running"; mods["motion-controller"].reason = "Activated: Path execution"; mods["motion-controller"].wakeCount = 1; mods["motion-controller"].lastActivation = 20; mods["motion-controller"].task = "Executing path";
  mods["perception-engine"].status = "sleeping"; mods["perception-engine"].reason = "Standby"; mods["perception-engine"].task = "Standby"; mods["perception-engine"].cpu = 0;
  mods["planning-engine"].status = "running"; mods["planning-engine"].reason = "Activated: Trajectory optimization"; mods["planning-engine"].wakeCount = 1; mods["planning-engine"].lastActivation = 20; mods["planning-engine"].task = "Active"; mods["planning-engine"].cpu = 12;
  const decision: Decision = { tick: 20, reason: "Obstacle cleared. Resuming primary mission.", wake: ["motion-controller", "planning-engine"], sleep: ["navigation-controller", "perception-engine"], suspend: [], priority: "Mission", hierarchy: ["Mission", "Safety", "Energy", "Memory"], decisionTimeMs: 0.45 };
  r.cpu = 18;
  m.battery.push(Math.round(r.battery * 10) / 10); m.cpu.push(18); m.memory.push(Math.round(38 + Math.random() * 3)); m.latency.push(0.45);
  m.missionUtility.push(Math.round(r.missionProgress * 10) / 10); m.safetyScore.push(96); m.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); m.eventsPerSec.push(Math.round(110 + Math.random() * 10));
  snapshots.push(buildSnap(20, w, r, mods, decision, t, m));
}

// Ticks 21-29
{
  const last = snapshots[snapshots.length - 1];
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  snapshots.push(...fillSnaps(21, 9, last.world, last.robot, last.modules, last.decision as Decision, t, m, (w, r, mods, _d, _t, _m2) => {
    nominalChange(w, r, mods, _d, _t, _m2); mods["motion-controller"].task = "Executing path"; mods["planning-engine"].task = "Idle"; mods["planning-engine"].reason = "Standby";
    for (const mod of Object.values(mods)) { if (mod.status !== "running") mod.cpu = 0; }
  }));
}

// Tick 30: Dust Storm
{
  const last = snapshots[snapshots.length - 1];
  const w = { ...last.world, cameraQuality: 0.1, lidarQuality: 0.3, commsQuality: 0.3, weather: "Dust Storm" };
  const r = { ...last.robot }; const mods = cloneMods(last.modules);
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  t.push({ tick: 30, time: 9000, event: "Dust Storm — sensors degraded", type: "warning" });
  mods["perception-engine"].status = "running"; mods["perception-engine"].reason = "Activated: Sensor fusion"; mods["perception-engine"].wakeCount = 2; mods["perception-engine"].lastActivation = 30; mods["perception-engine"].task = "Active";
  mods["safety-supervisor"].status = "running"; mods["safety-supervisor"].reason = "Activated: Comms degraded"; mods["safety-supervisor"].wakeCount = 1; mods["safety-supervisor"].lastActivation = 30; mods["safety-supervisor"].task = "Active";
  mods["motion-controller"].status = "suspended"; mods["motion-controller"].reason = "Reduced visibility"; mods["motion-controller"].task = "Suspended";
  const decision: Decision = { tick: 30, reason: "Dust storm detected. Sensors degraded. Perception Engine activated for sensor fusion.", wake: ["perception-engine", "safety-supervisor"], sleep: [], suspend: ["motion-controller"], priority: "Safety", hierarchy: ["Safety", "Mission", "Energy", "Memory"], decisionTimeMs: 0.91 };
  r.cpu = 30;
  m.battery.push(Math.round(r.battery * 10) / 10); m.cpu.push(30); m.memory.push(Math.round(45 + Math.random() * 3)); m.latency.push(0.91);
  m.missionUtility.push(Math.round(r.missionProgress * 10) / 10); m.safetyScore.push(78); m.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); m.eventsPerSec.push(Math.round(140 + Math.random() * 20));
  snapshots.push(buildSnap(30, w, r, mods, decision, t, m));
}

// Ticks 31-39
{
  const last = snapshots[snapshots.length - 1];
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  snapshots.push(...fillSnaps(31, 9, last.world, last.robot, last.modules, last.decision as Decision, t, m, (w, r, mods, _d, _t, _m2) => {
    r.battery = Math.max(0, r.battery - 0.4); r.missionProgress = Math.min(100, r.missionProgress + 1.0); r.cpu = 30 + Math.round(Math.random() * 5);
    for (const mod of Object.values(mods)) { if (mod.status === "running") { mod.totalRuntime += 1; mod.cpu = Math.round(6 + Math.random() * 14); } if (mod.status !== "running") mod.cpu = 0; }
    mods["perception-engine"].task = "Fusing degraded sensor data"; mods["perception-engine"].reason = "Degraded Visibility";
    mods["safety-supervisor"].task = "Alerting mission control"; mods["safety-supervisor"].reason = "Comms degraded";
    _m2.battery.push(Math.round(r.battery * 10) / 10); _m2.cpu.push(r.cpu); _m2.memory.push(Math.round(47 + Math.random() * 3));
    _m2.latency.push(Math.round((0.8 + Math.random() * 0.2) * 100) / 100); _m2.missionUtility.push(Math.round(r.missionProgress * 10) / 10);
    _m2.safetyScore.push(Math.round(72 + Math.random() * 5)); _m2.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); _m2.eventsPerSec.push(Math.round(145 + Math.random() * 15));
  }));
}

// Tick 40: Dust storm clears
{
  const last = snapshots[snapshots.length - 1];
  const w = { ...last.world, cameraQuality: 0.95, lidarQuality: 0.9, commsQuality: 0.7, weather: "Clear" };
  const r = { ...last.robot }; const mods = cloneMods(last.modules);
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  t.push({ tick: 40, time: 12000, event: "Dust storm passed. Sensors restored.", type: "success" });
  mods["perception-engine"].status = "sleeping"; mods["perception-engine"].reason = "Standby"; mods["perception-engine"].task = "Standby"; mods["perception-engine"].cpu = 0;
  mods["safety-supervisor"].status = "sleeping"; mods["safety-supervisor"].reason = "Standby"; mods["safety-supervisor"].task = "Standby"; mods["safety-supervisor"].cpu = 0;
  mods["motion-controller"].status = "running"; mods["motion-controller"].reason = "Activated: Navigation resumed"; mods["motion-controller"].wakeCount = 2; mods["motion-controller"].lastActivation = 40; mods["motion-controller"].task = "Executing path";
  mods["planning-engine"].status = "running"; mods["planning-engine"].reason = "Activated: Rerouting"; mods["planning-engine"].wakeCount = 2; mods["planning-engine"].lastActivation = 40; mods["planning-engine"].task = "Active";
  const decision: Decision = { tick: 40, reason: "Sensors restored. Resuming standard operation.", wake: ["motion-controller", "planning-engine"], sleep: ["perception-engine", "safety-supervisor"], suspend: [], priority: "Mission", hierarchy: ["Mission", "Safety", "Energy", "Memory"], decisionTimeMs: 0.38 };
  r.cpu = 22;
  m.battery.push(Math.round(r.battery * 10) / 10); m.cpu.push(22); m.memory.push(Math.round(40 + Math.random() * 3)); m.latency.push(0.38);
  m.missionUtility.push(Math.round(r.missionProgress * 10) / 10); m.safetyScore.push(94); m.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); m.eventsPerSec.push(Math.round(110 + Math.random() * 10));
  snapshots.push(buildSnap(40, w, r, mods, decision, t, m));
}

// Ticks 41-49
{
  const last = snapshots[snapshots.length - 1];
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  snapshots.push(...fillSnaps(41, 9, last.world, last.robot, last.modules, last.decision as Decision, t, m, (w, r, mods, _d, _t, _m2) => {
    nominalChange(w, r, mods, _d, _t, _m2); mods["motion-controller"].task = "Executing path"; mods["planning-engine"].task = "Idle";
    for (const mod of Object.values(mods)) { if (mod.status !== "running") mod.cpu = 0; }
  }));
}

// Tick 50: Battery Drain
{
  const last = snapshots[snapshots.length - 1];
  const w = { ...last.world }; const r = { ...last.robot, battery: 15 }; const mods = cloneMods(last.modules);
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  t.push({ tick: 50, time: 15000, event: "Critical battery — 15% remaining", type: "warning" });
  mods["motion-controller"].status = "suspended"; mods["motion-controller"].reason = "Low battery"; mods["motion-controller"].task = "Suspended";
  mods["safety-supervisor"].status = "running"; mods["safety-supervisor"].reason = "Activated: Power conservation"; mods["safety-supervisor"].wakeCount = 2; mods["safety-supervisor"].lastActivation = 50; mods["safety-supervisor"].task = "Active";
  mods["planning-engine"].status = "suspended"; mods["planning-engine"].reason = "Low battery"; mods["planning-engine"].task = "Suspended";
  mods["perception-engine"].status = "suspended"; mods["perception-engine"].reason = "Low battery"; mods["perception-engine"].task = "Suspended";
  const decision: Decision = { tick: 50, reason: "Low battery. Conserving power. Suspending non-critical modules.", wake: ["safety-supervisor"], sleep: [], suspend: ["motion-controller", "planning-engine", "perception-engine"], priority: "Energy", hierarchy: ["Energy", "Safety", "Mission", "Memory"], decisionTimeMs: 1.12 };
  r.cpu = 8; r.powerState = "Reduced";
  m.battery.push(15); m.cpu.push(8); m.memory.push(Math.round(35 + Math.random() * 3)); m.latency.push(1.12);
  m.missionUtility.push(Math.round(r.missionProgress * 10) / 10); m.safetyScore.push(88); m.energyHeadroom.push(3); m.eventsPerSec.push(Math.round(60 + Math.random() * 10));
  snapshots.push(buildSnap(50, w, r, mods, decision, t, m));
}

// Ticks 51-59
{
  const last = snapshots[snapshots.length - 1];
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  snapshots.push(...fillSnaps(51, 9, last.world, last.robot, last.modules, last.decision as Decision, t, m, (w, r, mods, _d, _t, _m2) => {
    r.battery = Math.max(0, r.battery - 0.15); r.missionProgress = Math.min(100, r.missionProgress + 1.0); r.cpu = 6 + Math.round(Math.random() * 3);
    for (const mod of Object.values(mods)) { if (mod.status === "running") { mod.totalRuntime += 1; mod.cpu = Math.round(2 + Math.random() * 4); } if (mod.status !== "running") mod.cpu = 0; }
    mods["safety-supervisor"].task = "Conserving power"; mods["safety-supervisor"].reason = "Low Power";
    _m2.battery.push(Math.round(r.battery * 10) / 10); _m2.cpu.push(r.cpu); _m2.memory.push(Math.round(32 + Math.random() * 3));
    _m2.latency.push(Math.round((1.0 + Math.random() * 0.3) * 100) / 100); _m2.missionUtility.push(Math.round(r.missionProgress * 10) / 10);
    _m2.safetyScore.push(Math.round(85 + Math.random() * 3)); _m2.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); _m2.eventsPerSec.push(Math.round(50 + Math.random() * 10));
  }));
}

// Ticks 60-69
{
  const last = snapshots[snapshots.length - 1];
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  snapshots.push(...fillSnaps(60, 10, last.world, last.robot, last.modules, last.decision as Decision, t, m, (w, r, mods, _d, _t, _m2) => {
    r.battery = Math.max(0, r.battery - 0.2); r.missionProgress = Math.min(100, r.missionProgress + 1.5); r.cpu = 12 + Math.round(Math.random() * 4);
    for (const mod of Object.values(mods)) { if (mod.status === "running") { mod.totalRuntime += 1; mod.cpu = Math.round(4 + Math.random() * 6); } if (mod.status !== "running") mod.cpu = 0; }
    mods["safety-supervisor"].task = "Idle"; mods["safety-supervisor"].reason = "Standby";
    _m2.battery.push(Math.round(r.battery * 10) / 10); _m2.cpu.push(r.cpu); _m2.memory.push(Math.round(35 + Math.random() * 3));
    _m2.latency.push(Math.round((0.6 + Math.random() * 0.2) * 100) / 100); _m2.missionUtility.push(Math.round(r.missionProgress * 10) / 10);
    _m2.safetyScore.push(Math.round(90 + Math.random() * 3)); _m2.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); _m2.eventsPerSec.push(Math.round(80 + Math.random() * 10));
  }));
}

// Ticks 70-79
{
  const last = snapshots[snapshots.length - 1];
  const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  snapshots.push(...fillSnaps(70, 10, last.world, last.robot, last.modules, last.decision as Decision, t, m, (w, r, mods, _d, _t, _m2) => {
    nominalChange(w, r, mods, _d, _t, _m2);
    for (const mod of Object.values(mods)) { if (mod.status !== "running") mod.cpu = 0; }
  }));
}

// Tick 80: Complete
{
  const last = snapshots[snapshots.length - 1];
  const w = { ...last.world }; const r = { ...last.robot, missionProgress: 100, battery: last.robot.battery, powerState: "Nominal" };
  const mods = cloneMods(last.modules); const t = last.eventHistory.map(e => ({ ...e })); const m: Record<string, number[]> = {};
  for (const [k, arr] of Object.entries(last.metrics)) m[k] = [...arr];
  t.push({ tick: 80, time: 24000, event: "Mission complete. Sample site reached.", type: "success" });
  const decision: Decision = { tick: 80, reason: "Mission objective achieved.", wake: [], sleep: [], suspend: [], priority: "Mission", hierarchy: ["Mission", "Safety", "Energy", "Memory"], decisionTimeMs: 0.2 };
  m.battery.push(Math.round(r.battery * 10) / 10); m.cpu.push(10); m.memory.push(Math.round(30 + Math.random() * 3)); m.latency.push(0.2);
  m.missionUtility.push(100); m.safetyScore.push(98); m.energyHeadroom.push(Math.round((r.battery * 0.2) * 10) / 10); m.eventsPerSec.push(Math.round(50 + Math.random() * 10));
  snapshots.push(buildSnap(80, w, r, mods, decision, t, m));
}

const trace: TraceData = {
  version: "0.1.0",
  schemaVersion: "1",
  metadata: METADATA,
  events: { "Rockslide": 10, "Dust Storm": 30, "Battery Drain": 50 },
  snapshots,
};

const outPath = path.resolve(__dirname, "..", "public", "data", "runtime-trace.json");
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(trace, null, 1), "utf-8");
console.log(`Wrote ${snapshots.length} snapshots to ${outPath}`);
