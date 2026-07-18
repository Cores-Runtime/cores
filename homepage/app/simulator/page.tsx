"use client";

import Link from "next/link";
import { RuntimeProvider } from "@/components/simulator/RuntimeContext";
import { MissionStatus } from "@/components/simulator/MissionStatus";
import { RobotState } from "@/components/simulator/RobotState";
import { RuntimeModules } from "@/components/simulator/RuntimeModules";
import { SchedulerPanel } from "@/components/simulator/SchedulerPanel";
import { DecisionTimeline } from "@/components/simulator/DecisionTimeline";
import { ScenarioControls } from "@/components/simulator/ScenarioControls";
import { MetricsPanel } from "@/components/simulator/MetricsPanel";
import { DecisionExplanation } from "@/components/simulator/DecisionExplanation";

export default function SimulatorPage() {
  return (
    <RuntimeProvider>
      <div className="min-h-screen bg-paper">
        <nav className="fixed top-0 left-0 right-0 z-50 bg-paper/80 backdrop-blur-md border-b border-border">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-bold text-ink text-base">
              <span className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-paper font-mono text-xs">CR</span>
              CORES
            </Link>
            <div className="flex items-center gap-3">
              <Link href="/simulator/replay" className="text-[11px] text-muted/50 hover:text-ink transition-colors">
                3D Replay
              </Link>
              <span className="text-xs font-mono text-muted/50">Dashboard v0.2</span>
            </div>
          </div>
        </nav>

        <main className="pt-14 pb-10 px-4 md:px-6 max-w-7xl mx-auto">
          <div className="pt-6 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-ink tracking-tight">Mission Control</h1>
                <p className="text-sm text-muted/60 mt-0.5">CORES Runtime Simulator — live dashboard</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <MissionStatus />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 flex flex-col gap-4">
                <MetricsPanel />
                <DecisionTimeline />
              </div>
              <div className="flex flex-col gap-4">
                <RobotState />
                <SchedulerPanel />
              </div>
            </div>

            <RuntimeModules />
            <ScenarioControls />
            <DecisionExplanation />
          </div>
        </main>
      </div>
    </RuntimeProvider>
  );
}
