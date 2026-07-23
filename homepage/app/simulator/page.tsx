"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { RuntimeProvider, type SimulatorMode } from "@/components/simulator/RuntimeContext";
import { MissionBar } from "@/components/simulator/MissionBar";
import { RobotState } from "@/components/simulator/RobotState";
import { RuntimeModules } from "@/components/simulator/RuntimeModules";
import { SchedulerPanel } from "@/components/simulator/SchedulerPanel";
import { DecisionTimeline } from "@/components/simulator/DecisionTimeline";
import { ScenarioControls } from "@/components/simulator/ScenarioControls";
import { MetricsPanel } from "@/components/simulator/MetricsPanel";

function SimulatorInner() {
  const searchParams = useSearchParams();
  const modeParam = searchParams.get("mode");
  const initialMode: SimulatorMode = modeParam === "live" ? "live" : "replay";

  return (
    <RuntimeProvider initialMode={initialMode}>
      <div className="min-h-screen bg-canvas-white">
        <nav className="fixed top-0 left-0 right-0 z-50 bg-canvas-white border-b border-mist">
          <div className="max-w-page mx-auto px-6 h-12 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <span className="font-display text-[13px] tracking-tight text-graphite">CORES</span>
              <span className="font-sans text-[11px] text-slate">Simulator</span>
            </Link>
            <div className="flex items-center gap-4">
              <Link href="/simulator/replay" className="font-sans text-[12px] text-slate hover:text-graphite transition-colors">
                3D Replay
              </Link>
              <span className="font-sans text-[11px] text-slate/60">v0.2</span>
            </div>
          </div>
        </nav>

        <main className="pt-12 pb-12 px-4 md:px-6 max-w-page mx-auto">
          <div className="pt-6 pb-6">
            <MissionBar />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
            <div className="lg:col-span-2 space-y-5">
              <MetricsPanel />
              <DecisionTimeline />
            </div>
            <div className="space-y-5">
              <RobotState />
              <SchedulerPanel />
            </div>
          </div>

          <RuntimeModules />
          <ScenarioControls />
        </main>
      </div>
    </RuntimeProvider>
  );
}

export default function SimulatorPage() {
  return (
    <Suspense>
      <SimulatorInner />
    </Suspense>
  );
}
