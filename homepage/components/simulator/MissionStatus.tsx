"use client";

import { useSimulator } from "./RuntimeContext";

export function MissionStatus() {
  const { engine, tick } = useSimulator();
  const r = engine.robot;
  const statusColor = (v: number) => v > 50 ? "bg-emerald-500" : v > 20 ? "bg-amber-500" : "bg-red-500";

  const stat = (label: string, val: string | number, unit?: string) => (
    <div key={label} className="text-center">
      <div className="text-[10px] text-muted/50 uppercase tracking-wider">{label}</div>
      <div className="text-sm font-bold text-ink">{val}{unit || ""}</div>
    </div>
  );

  return (
    <div className="col-span-full glass p-5 grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-4 items-center">
      <div className="flex items-center gap-3 col-span-2 md:col-span-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" style={{ animationDuration: "2s" }} />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
        </span>
        <div>
          <div className="text-xs text-muted/50 uppercase tracking-wider">Mission</div>
          <div className="text-base font-bold text-ink">{engine.activeMission?.name || "No Mission"}</div>
        </div>
      </div>
      {stat("Status", "Running")}
      {stat("Progress", Math.round(r.missionProgress), "%")}
      {stat("Battery", Math.round(r.battery), "%")}
      {stat("CPU", r.cpu, "%")}
      {stat("Memory", r.memory, "%")}
      {stat("Temp", Math.round(engine.world.temperature), "°C")}
      {stat("Ticks", tick)}
    </div>
  );
}
