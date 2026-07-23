"use client";

import { createContext, useContext, useEffect, useState, useRef, useCallback, type ReactNode } from "react";
import { ReplayRuntimeSource } from "@/lib/replay-source";
import { LiveRuntimeSource } from "@/lib/live-source";
import { JsonTraceLoader } from "@/lib/json-trace-loader";
import type { SimulatorState, MissionInfo, TraceSnapshot } from "@/lib/runtime-types";
import type { EventInfo } from "@/lib/runtime-source";

export type SimulatorMode = "replay" | "live";

type EngineProxy = SimulatorState & {
  getModuleDef: (id: string) => { id: string; name: string; priority: number; cpuCost: number; deps: string[]; purpose: string } | undefined;
  activeMission: (MissionInfo & { modules: { id: string; name: string; priority: number; cpuCost: number; deps: string[]; purpose: string }[] }) | null;
  timeline: SimulatorState["eventHistory"];
};

export type SimulatorValue = {
  state: SimulatorState;
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
  mode: SimulatorMode;
  setMode: (mode: SimulatorMode) => void;
  wsUrl: string;
  setWsUrl: (url: string) => void;
};

const DEFAULT_WS_URL = "ws://127.0.0.1:8765";

const SimulatorCtx = createContext<SimulatorValue | null>(null);

export function RuntimeProvider({
  children,
  initialMode = "replay",
}: {
  children: ReactNode;
  initialMode?: SimulatorMode;
}) {
  const [mode, setMode_] = useState<SimulatorMode>(initialMode);
  const [wsUrl, setWsUrl_] = useState(DEFAULT_WS_URL);
  const replayRef = useRef<ReplayRuntimeSource | null>(null);
  const liveRef = useRef<LiveRuntimeSource | null>(null);
  const [, forceRender] = useState(0);
  const [ready, setReady] = useState(false);

  const initReplay = useCallback(() => {
    if (replayRef.current) return;
    const loader = new JsonTraceLoader("/data/runtime-trace.json");
    const p = new ReplayRuntimeSource(loader);
    replayRef.current = p;
    p.init().then(() => {
      if (p.availableMissions.length > 0) {
        p.loadMission(p.availableMissions[0].id);
        p.setStatus("running");
      }
      setReady(true);
    });
    p.subscribe(() => forceRender(v => v + 1));
  }, []);

  const initLive = useCallback(() => {
    if (liveRef.current) {
      liveRef.current.destroy();
      liveRef.current = null;
    }
    const ls = new LiveRuntimeSource(wsUrl);
    liveRef.current = ls;
    ls.init().then(() => {
      setReady(true);
    });
    ls.subscribe(() => forceRender(v => v + 1));
  }, [wsUrl]);

  useEffect(() => {
    setReady(false);
    if (mode === "replay") {
      if (liveRef.current) {
        liveRef.current.destroy();
        liveRef.current = null;
      }
      initReplay();
    } else {
      if (replayRef.current) {
        replayRef.current = null as any;
      }
      initLive();
    }
  }, [mode, initReplay, initLive]);

  const setMode = useCallback((newMode: SimulatorMode) => {
    setMode_(newMode);
  }, []);

  const setWsUrl = useCallback((url: string) => {
    setWsUrl_(url);
  }, []);

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-paper">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <div className="text-sm text-muted/50">
            {mode === "replay" ? "Booting CORES runtime..." : "Connecting to live runtime..."}
          </div>
        </div>
      </div>
    );
  }

  const source = mode === "replay" ? replayRef.current : liveRef.current;
  if (!source) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-paper">
        <div className="text-sm text-muted/50">No runtime source available</div>
      </div>
    );
  }

  const state = source.getState();

  const cumulativeMetrics = (() => {
    if (mode === "live") return state.metrics;
    const snapshots = (replayRef.current as any)?.snapshots as readonly TraceSnapshot[] | undefined;
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
    setRunning: (v) => {
      if (mode === "replay") replayRef.current?.setStatus(v ? "running" : "paused");
    },
    missions: source.availableMissions as any,
    mission: state.mission as any,
    injectableEvents: source.availableEvents as any,
    injectEvent: (name) => {
      if (mode === "replay") replayRef.current?.dispatchEvent(name);
    },
    loadMission: (id) => {
      if (mode === "replay") replayRef.current?.loadMission(id);
    },
    seek: (tick) => {
      if (mode === "replay") replayRef.current?.seek(tick);
    },
    totalTicks: source.totalTicks(),
    engine: new Proxy(state as any, {
      get: (target, prop) => {
        const s = target as SimulatorState;
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
    mode,
    setMode,
    wsUrl,
    setWsUrl,
  };

  return <SimulatorCtx.Provider value={value}>{children}</SimulatorCtx.Provider>;
}

export function useSimulator(): SimulatorValue {
  const v = useContext(SimulatorCtx);
  if (!v) throw new Error("useSimulator must be used within RuntimeProvider");
  return v;
}
