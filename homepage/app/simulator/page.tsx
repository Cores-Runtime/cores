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
            <span className="text-xs font-mono text-muted/50">Runtime Simulator v0.2</span>
          </div>
        </nav>

        <main className="pt-14 pb-10 px-4 md:px-6 max-w-7xl mx-auto">
          <div className="text-center py-8">
            <h1 className="text-2xl md:text-3xl font-bold text-ink tracking-tight">CORES Runtime Simulator</h1>
            <p className="text-sm text-muted/60 mt-1">Mission control dashboard — select a mission to begin</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 auto-rows-min">
            <MissionStatus />
            <RobotState />
            <RuntimeModules />
            <SchedulerPanel />
            <DecisionTimeline />
            <ScenarioControls />
            <MetricsPanel />
            <DecisionExplanation />
          </div>
        </main>
      </div>
      </RuntimeProvider>
  );
}
