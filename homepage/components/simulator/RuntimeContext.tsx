"use client";

import { createContext, useContext, useEffect, useState, useRef, type ReactNode } from "react";
import { ReplayRuntimeSource } from "@/lib/replay-source";
import { JsonTraceLoader } from "@/lib/json-trace-loader";
import type { RuntimeState, MissionInfo, TraceSnapshot } from "@/lib/runtime-types";
import type { EventInfo } from "@/lib/runtime-source";

type EngineProxy = RuntimeState & {
  getModuleDef: (id: string) => { id: string; name: string; priority: number; cpuCost: number; deps: string[]; purpose: string } | undefined;
  activeMission: (MissionInfo & { modules: { id: string; name: string; priority: number; cpuCost: number; deps: string[]; purpose: string }[] }) | null;
  /** @deprecated Use eventHistory */
  timeline: RuntimeState["eventHistory"];
};

export type SimulatorValue = {
  state: RuntimeState;
  running: boolean;
  setRunning: (v: boolean) => void;
  missions: { id: string; name: string; desc: string; constraints: string[] }[];
  mission: MissionInfo | null;
  injectableEvents: EventInfo[];
  injectEvent: (name: string) => void;
  loadMission: (id: string) => void;
  seek: (tick: number) => void;
  totalTicks: number;
  tick: number;
  engine: EngineProxy;
};

const SimulatorCtx = createContext<SimulatorValue | null>(null);

export function RuntimeProvider({ children }: { children: ReactNode }) {
  const providerRef = useRef<ReplayRuntimeSource | null>(null);
  const [, forceRender] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const loader = new JsonTraceLoader("/data/runtime-trace.json");
    const p = new ReplayRuntimeSource(loader);
    providerRef.current = p;
    p.init().then(() => {
      if (p.availableMissions.length > 0) {
        p.loadMission(p.availableMissions[0].id);
        p.setStatus("running");
      }
      setReady(true);
    });
    p.subscribe(() => forceRender(v => v + 1));
  }, []);

  if (!ready || !providerRef.current) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-paper">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <div className="text-sm text-muted/50">Booting CORES runtime...</div>
        </div>
      </div>
    );
  }

  const p = providerRef.current;
  const state = p.getState();

  const cumulativeMetrics = (() => {
    const snapshots = (p as any).snapshots as readonly TraceSnapshot[] | undefined;
    if (!snapshots || snapshots.length === 0) return {} as Record<string, number[]>;
    const keys = Object.keys(snapshots[0].metrics ?? {});
    if (keys.length === 0) return {} as Record<string, number[]>;
    const curIndex = snapshots.findIndex(s => s.tick >= state.tick);
    const untilIndex = curIndex >= 0 ? curIndex : snapshots.length - 1;
    const acc: Record<string, number[]> = {};
    for (const k of keys) {
      const arr: number[] = [];
      for (let i = 0; i <= untilIndex; i++) {
        const vals = snapshots[i].metrics?.[k];
        if (vals && vals.length > 0) arr.push(vals[vals.length - 1]);
      }
      if (arr.length > 0) acc[k] = arr;
    }
    return acc;
  })();

  const value: SimulatorValue = {
    state,
    tick: state.tick,
    running: state.status === "running",
    setRunning: (v) => providerRef.current?.setStatus(v ? "running" : "paused"),
    missions: p.availableMissions as any,
    mission: state.mission as any,
    injectableEvents: p.availableEvents as any,
    injectEvent: (name) => providerRef.current?.dispatchEvent(name),
    loadMission: (id) => providerRef.current?.loadMission(id),
    seek: (tick) => providerRef.current?.seek(tick),
    totalTicks: providerRef.current?.totalTicks() ?? 0,
    engine: new Proxy(state as any, {
      get: (target, prop) => {
        const s = target as RuntimeState;
        if (prop === "metrics") return cumulativeMetrics;
        if (prop === "activeMission") {
          if (!s.mission) return null;
          return { ...s.mission, modules: s.moduleDefs };
        }
        if (prop === "getModuleDef") {
          return (id: string) => s.moduleDefs.find((m: any) => m.id === id);
        }
        if (prop === "timeline") {
          return s.eventHistory;
        }
        return (s as any)[prop];
      },
    }) as unknown as EngineProxy,
  };

  return <SimulatorCtx.Provider value={value}>{children}</SimulatorCtx.Provider>;
}

export function useSimulator(): SimulatorValue {
  const v = useContext(SimulatorCtx);
  if (!v) throw new Error("useSimulator must be used within RuntimeProvider");
  return v;
}
