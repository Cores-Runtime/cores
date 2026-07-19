"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import NextDynamic from "next/dynamic";
import { RuntimeProvider, useSimulator } from "@/components/simulator/RuntimeContext";
import { PATH_LENGTH } from "@/lib/path-constants";
import type { CameraPreset } from "@/components/simulator/replay/MarsScene";

const MarsScene = NextDynamic(() => import("@/components/simulator/replay/MarsScene").then(m => ({ default: m.MarsScene })), { ssr: false });

const CAMERA_PRESETS: { key: CameraPreset; label: string; icon: string }[] = [
  { key: "free", label: "Free", icon: "⟳" },
  { key: "cinematic", label: "Cinematic", icon: "🎬" },
  { key: "topdown", label: "Top Down", icon: "⬇" },
  { key: "thirdperson", label: "Follow", icon: "🎯" },
];

const EVENT_BUTTONS = ["Rockslide", "Dust Storm", "Battery Drain", "Goal Reached"];

function ReplayControls() {
  const { state, running, setRunning, seek, tick, totalTicks, injectEvent } = useSimulator();
  const maxTick = totalTicks > 0 ? totalTicks - 1 : 0;

  return (
    <div className="flex flex-col gap-2">
      <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-xl p-3 flex items-center gap-3">
        <button
          className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center hover:bg-accent/20 transition-colors shrink-0"
          onClick={() => seek(0)}
          title="Reset"
        >
          <svg className="w-3.5 h-3.5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
          </svg>
        </button>

        <button
          className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center hover:bg-accentHover transition-colors shrink-0"
          onClick={() => setRunning(!running)}
          title={running ? "Pause" : "Play"}
        >
          {running ? (
            <svg className="w-3.5 h-3.5 text-paper" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5 text-paper" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        <div className="flex-1 flex items-center gap-2 min-w-0">
          <input
            type="range"
            min={0}
            max={maxTick}
            value={Math.min(tick, maxTick)}
            onChange={(e) => seek(Number(e.target.value))}
            className="flex-1 h-1.5 rounded-full appearance-none bg-white/20 cursor-pointer accent-accent
              [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5
              [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:shadow-md"
          />
          <span className="text-[11px] font-mono text-white/50 w-16 text-right shrink-0">
            T{tick}/{maxTick}
          </span>
        </div>
      </div>

      <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-xl p-2 flex items-center gap-2 flex-wrap">
        {EVENT_BUTTONS.map((evt) => (
          <button
            key={evt}
            onClick={() => injectEvent(evt)}
            className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-[10px] text-white/60 hover:bg-white/10 hover:text-white transition-colors"
          >
            {evt}
          </button>
        ))}
      </div>
    </div>
  );
}

import type { SimulatorState } from "@/lib/runtime-types";

function computeMissionStats(state: SimulatorState): {
  distance: string; energyUsed: string; modulesActivated: number;
  safetyEvents: number; decisions: number; missionTime: string;
} {
  const energyUsed = Math.round(Math.abs(100 - state.robot.battery));
  const modulesActivated = Object.values(state.modules).filter(m => m.wakeCount > 0).length;
  const safetyEvents = state.eventHistory.filter(e => e.type === "warning").length;
  const decisions = state.tick;
  const totalSecs = Math.round(state.tick * 1.2);
  const mins = Math.floor(totalSecs / 60);
  const secs = totalSecs % 60;
  return {
    distance: `${PATH_LENGTH} m`,
    energyUsed: `${energyUsed}%`,
    modulesActivated,
    safetyEvents,
    decisions,
    missionTime: mins > 0 ? `${mins}m ${secs}s` : `${secs}s`,
  };
}

function StatCard({ icon, label, value, delay }: { icon: string; label: string; value: string; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
      className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.07] transition-colors"
    >
      <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
        <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={icon} />
        </svg>
      </div>
      <div>
        <div className="text-base font-bold text-white tabular-nums tracking-tight">{value}</div>
        <div className="text-[10px] text-white/40 font-medium">{label}</div>
      </div>
    </motion.div>
  );
}

function MissionCompleteOverlay({ state, onOpenDashboard, onReplay }: { state: SimulatorState; onOpenDashboard: () => void; onReplay: () => void }) {
  const stats = useMemo(() => computeMissionStats(state), [state.tick]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 backdrop-blur-sm"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="relative max-w-sm w-full mx-4"
      >
        <div className="absolute -inset-1 bg-gradient-to-b from-accent/20 via-transparent to-transparent rounded-3xl blur-xl opacity-60" />

        <div className="relative bg-[#0d0d0d] border border-white/[0.08] rounded-2xl shadow-2xl overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />

          <div className="px-6 pt-7 pb-5 text-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.25, ease: "easeOut" }}
              className="relative w-14 h-14 mx-auto mb-4"
            >
              <svg className="w-14 h-14" viewBox="0 0 56 56">
                <circle cx="28" cy="28" r="25" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
                <circle cx="28" cy="28" r="25" fill="none" stroke="currentColor" strokeWidth="3"
                  strokeDasharray={`${2 * Math.PI * 25}`} strokeDashoffset="0"
                  className="text-accent" transform="rotate(-90 28 28)"
                  style={{ strokeDashoffset: `${2 * Math.PI * 25 * 0}`, transition: "stroke-dashoffset 1s ease" }}
                />
                <text x="28" y="28" textAnchor="middle" dominantBaseline="central"
                  className="text-[13px] font-bold fill-white" fontSize="13" fontWeight="700">100%</text>
              </svg>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.35 }}
              className="text-2xl font-bold text-white tracking-tight"
            >
              Mission Complete
            </motion.h2>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.45 }}
              className="text-xs text-white/40 mt-1"
            >
              {state.mission?.name ?? "Surface Survey"}
            </motion.p>
          </div>

          <div className="px-6 pb-5">
            <div className="grid grid-cols-2 gap-2.5">
              <StatCard icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" label="Distance" value={stats.distance} delay={0.5} />
              <StatCard icon="M13 10V3L4 14h7v7l9-11h-7z" label="Energy Used" value={stats.energyUsed} delay={0.55} />
              <StatCard icon="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" label="Modules" value={String(stats.modulesActivated)} delay={0.6} />
              <StatCard icon="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" label="Safety Events" value={String(stats.safetyEvents)} delay={0.65} />
              <StatCard icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" label="Decisions" value={String(stats.decisions)} delay={0.7} />
              <StatCard icon="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" label="Mission Time" value={stats.missionTime} delay={0.75} />
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.85 }}
            className="px-6 pb-6 flex flex-col gap-2"
          >
            <button
              onClick={onOpenDashboard}
              className="w-full py-2.5 rounded-xl bg-accent text-paper font-bold text-sm hover:brightness-110 transition-all flex items-center justify-center gap-2"
            >
              Open Dashboard
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
            <button
              onClick={onReplay}
              className="w-full py-2 rounded-xl border border-white/10 text-[11px] text-white/40 hover:text-white/70 hover:border-white/20 transition-all"
            >
              Replay Mission
            </button>
          </motion.div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function CognitionStream({ state }: { state: SimulatorState }) {
  const [steps, setSteps] = useState<{ id: number; text: string; icon: string; color: string }[]>([]);
  const processedTickRef = useRef(-1);
  const processedEventsLen = useRef(0);
  const idCounter = useRef(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const tick = state.tick;
    const decision = state.decision;
    const evLen = state.eventHistory.length;
    const newEvent = evLen > processedEventsLen.current;
    const newTick = tick !== processedTickRef.current;

    if (!newTick) return;

    processedTickRef.current = tick;
    processedEventsLen.current = evLen;

    timers.current.forEach(t => clearTimeout(t));
    timers.current = [];

    const chain: { id: number; text: string; icon: string; color: string }[] = [];
    const add = (text: string, icon: string, color: string) => {
      chain.push({ id: idCounter.current++, text, icon, color });
    };

    if (newEvent) {
      const lastEvent = state.eventHistory[evLen - 1];
      if (lastEvent) {
        if (lastEvent.type === "warning") {
          add(`⚠ ${lastEvent.event}`, "⚠", "text-red-400");
        } else if (lastEvent.type === "success") {
          add(`✓ ${lastEvent.event}`, "✓", "text-emerald-400");
        } else {
          add(`● ${lastEvent.event}`, "●", "text-accent");
        }
      }
    }

    if (decision) {
      if (chain.length > 0) {
        add("", "", "");
      }

      add(`🤔 ${decision.reason}`, "🤔", "text-accent font-bold");

      decision.wake.forEach((m) => {
        const mod = state.modules[m];
        const task = mod?.task || "Initializing...";
        add(`🟢 ${m} ${task}`, "🟢", "text-emerald-400");
      });

      decision.sleep?.forEach((m) => {
        add(`⚪ ${m} sleeping`, "⚪", "text-white/40");
      });

      decision.suspend.forEach((m) => {
        const mod = state.modules[m];
        const reason = mod?.reason || "Suspended";
        add(`🔴 ${m} ${reason}`, "🔴", "text-red-400");
      });
    }

    chain.forEach((step, i) => {
      if (!step.text) return;
      const t1 = setTimeout(() => {
        setSteps(prev => [...prev, step]);
        const t2 = setTimeout(() => {
          setSteps(prev => prev.filter(s => s.id !== step.id));
        }, 7000);
        timers.current.push(t2);
      }, i * 350);
      timers.current.push(t1);
    });

    return () => timers.current.forEach(t => clearTimeout(t));
  }, [state.tick]);

  if (steps.length === 0) return null;

  return (
    <div className="absolute left-4 top-1/2 -translate-y-1/2 z-20 flex flex-col gap-2 max-w-[280px] pointer-events-none">
      {steps.map((step) => (
        <motion.div
          key={step.id}
          initial={{ opacity: 0, x: -24, scale: 0.95 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: -12, scale: 0.95 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className={`px-3 py-1.5 rounded-lg backdrop-blur-md border border-white/[0.06] text-[11px] leading-relaxed ${step.color}`}
          style={{ background: "rgba(0,0,0,0.6)" }}
        >
          {step.icon} {step.text}
        </motion.div>
      ))}
    </div>
  );
}

function ModuleActivityFeed({ state }: { state: SimulatorState }) {
  const [cards, setCards] = useState<{ id: number; name: string; text: string; color: string }[]>([]);
  const prevModulesRef = useRef(state.modules);
  const processedTickRef = useRef(-1);
  const idCounter = useRef(0);

  useEffect(() => {
    if (state.tick === processedTickRef.current) return;
    processedTickRef.current = state.tick;

    const prev = prevModulesRef.current;
    const curr = state.modules;
    prevModulesRef.current = curr;

    const newCards: { id: number; name: string; text: string; color: string }[] = [];

    for (const [id, mod] of Object.entries(curr)) {
      const p = prev[id];
      if (!p) continue;

      if (mod.status === "running" && p.status !== "running") {
        newCards.push({ id: idCounter.current++, name: id, text: mod.task || "Executing...", color: "text-emerald-400" });
      } else if (mod.status === "thinking" && p.status !== "thinking") {
        newCards.push({ id: idCounter.current++, name: id, text: mod.reason || "Computing...", color: "text-amber-400" });
      } else if (mod.status === "suspended" && p.status !== "suspended") {
        newCards.push({ id: idCounter.current++, name: id, text: mod.reason || "Suspended", color: "text-red-400" });
      } else if (mod.task !== p.task && mod.status === "running") {
        newCards.push({ id: idCounter.current++, name: id, text: mod.task, color: "text-emerald-300" });
      }
    }

    if (newCards.length > 0) {
      setCards(prev => [...prev, ...newCards]);
      const ids = newCards.map(c => c.id);
      setTimeout(() => setCards(prev => prev.filter(c => !ids.includes(c.id))), 3500);
    }
  }, [state.tick]);

  if (cards.length === 0) return null;

  return (
    <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-1.5 pointer-events-none">
      {cards.slice(-6).map((card) => (
        <motion.div
          key={card.id}
          initial={{ opacity: 0, y: 12, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.95 }}
          transition={{ duration: 0.25 }}
          className={`px-3 py-1 rounded-lg backdrop-blur-md border border-white/[0.06] text-[11px] font-mono ${card.color}`}
          style={{ background: "rgba(0,0,0,0.6)" }}
        >
          {card.name}: {card.text}
        </motion.div>
      ))}
    </div>
  );
}

function RuntimeHUD({ state }: { state: SimulatorState }) {
  const w = state.world;
  const r = state.robot;
  const navActive = state.modules["navigation-controller"]?.status === "running";
  const stormActive = w.weather === "Dust Storm";
  const lowBattery = r.battery < 25;
  const obstacleNear = w.obstacleDistance < 1;

  return (
    <div className="absolute top-14 left-3 right-3 flex justify-between pointer-events-none" style={{ zIndex: 15 }}>
      <div className="flex gap-2">
        {obstacleNear && (
          <div className="px-2 py-1 rounded-lg bg-red-500/20 border border-red-500/30 text-[10px] font-bold text-red-500 uppercase tracking-wider animate-pulse">
            Obstacle {w.obstacleDistance.toFixed(1)}m
          </div>
        )}
        {navActive && (
          <div className="px-2 py-1 rounded-lg bg-orange-500/20 border border-orange-500/30 text-[10px] font-bold text-orange-500 uppercase tracking-wider">
            Navigation Controller
          </div>
        )}
        {stormActive && (
          <div className="px-2 py-1 rounded-lg bg-amber-500/20 border border-amber-500/30 text-[10px] font-bold text-amber-500 uppercase tracking-wider">
            Dust Storm
          </div>
        )}
        {lowBattery && (
          <div className="px-2 py-1 rounded-lg bg-red-500/20 border border-red-500/30 text-[10px] font-bold text-red-500 uppercase tracking-wider animate-pulse">
            Low Battery {Math.round(r.battery)}%
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <div className="px-2 py-1 rounded-lg bg-white/10 text-[10px] text-white/70">
          {w.terrain} | {Math.round(r.missionProgress)}%
        </div>
      </div>
    </div>
  );
}

function MissionPanel({ state }: { state: SimulatorState }) {
  const r = state.robot;
  const lowBattery = r.battery < 25;
  return (
    <div className="absolute top-14 left-3 z-20 pointer-events-none max-w-[200px]">
      <div className="px-3 py-2 rounded-xl bg-black/50 backdrop-blur-md border border-white/10">
        <div className="text-xs font-bold text-white/90">{state.mission?.name ?? "No Mission"}</div>
        <div className="text-[9px] text-white/50 mt-0.5 leading-tight">{state.mission?.desc ?? ""}</div>
        <div className="flex items-center gap-2 mt-1.5">
          <div className="flex-1 h-1 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(100, r.missionProgress)}%`,
                background: lowBattery ? "linear-gradient(90deg, #EF4444, #DC2626)" : "linear-gradient(90deg, #10B981, #34D399)",
              }}
            />
          </div>
          <span className="text-[9px] font-mono text-white/50">{Math.round(r.missionProgress)}%</span>
        </div>
      </div>
    </div>
  );
}

function CameraPresetBar({ preset, onChange }: { preset: CameraPreset; onChange: (p: CameraPreset) => void }) {
  return (
    <div className="absolute top-14 right-3 z-20 flex gap-1">
      {CAMERA_PRESETS.map((p) => (
        <button
          key={p.key}
          onClick={() => onChange(p.key)}
          className={`px-2 py-1 rounded-lg text-[10px] transition-all ${
            preset === p.key
              ? "bg-accent text-paper font-bold"
              : "bg-black/40 text-white/50 hover:bg-white/10 hover:text-white border border-white/10"
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

function ReplayPageInner() {
  const { state, seek, setRunning } = useSimulator();
  const router = useRouter();
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>("free");
  const missionComplete = state.robot.missionProgress >= 100;
  const [showOverlay, setShowOverlay] = useState(false);
  const overlayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (missionComplete && !showOverlay && !overlayTimerRef.current) {
      setRunning(false);
      overlayTimerRef.current = setTimeout(() => {
        setShowOverlay(true);
        overlayTimerRef.current = null;
      }, 1200);
    }
    if (!missionComplete) {
      if (overlayTimerRef.current) {
        clearTimeout(overlayTimerRef.current);
        overlayTimerRef.current = null;
      }
      setShowOverlay(false);
    }
    return () => {
      if (overlayTimerRef.current) clearTimeout(overlayTimerRef.current);
    };
  }, [missionComplete, showOverlay, setRunning]);

  return (
    <div className="fixed inset-0 bg-black">
      <nav className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-b from-black/60 to-transparent">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-white/90 text-sm">
            <span className="w-6 h-6 rounded-lg bg-accent flex items-center justify-center text-paper font-mono text-[10px]">CR</span>
            CORES
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/simulator" className="text-[11px] text-white/50 hover:text-white transition-colors">
              Dashboard
            </Link>
            <span className="text-[11px] font-mono text-white/40">Replay v0.1</span>
          </div>
        </div>
      </nav>

      <RuntimeHUD state={state} />
      <CognitionStream state={state} />
      <ModuleActivityFeed state={state} />
      {!showOverlay && <MissionPanel state={state} />}
      <CameraPresetBar preset={cameraPreset} onChange={setCameraPreset} />
      <MarsScene state={state} cameraPreset={cameraPreset} />

      {showOverlay && (
        <MissionCompleteOverlay
          state={state}
          onOpenDashboard={() => router.push("/simulator")}
          onReplay={() => {
            setShowOverlay(false);
            seek(0);
            setRunning(true);
          }}
        />
      )}

      <div className={`absolute bottom-0 left-0 right-0 z-20 bg-gradient-to-t from-black/60 to-transparent pt-12 pb-4 px-4 transition-opacity duration-500 ${showOverlay ? "opacity-0 pointer-events-none" : ""}`}>
        <ReplayControls />
      </div>
    </div>
  );
}

export default function ReplayPage() {
  return (
    <RuntimeProvider>
      <ReplayPageInner />
    </RuntimeProvider>
  );
}
