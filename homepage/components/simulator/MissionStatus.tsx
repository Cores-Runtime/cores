"use client";

import { useSimulator } from "./RuntimeContext";

function Bar({ value, label, color, danger }: { value: number; label: string; color: string; danger?: boolean }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-muted/50 w-14 text-right">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-white/30 border border-white/10 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ease-out ${danger && pct < 25 ? "bg-red-500" : color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-mono font-bold text-ink w-10 text-right">{Math.round(pct)}%</span>
    </div>
  );
}

export function MissionStatus() {
  const { engine, tick, running } = useSimulator();
  const r = engine.robot;
  const m = engine.metrics;

  const latest = (key: string) => {
    const arr = m[key];
    return arr && arr.length > 0 ? arr[arr.length - 1] : 0;
  };

  return (
    <div className="col-span-full glass p-4">
      <div className="flex items-center gap-4 mb-3 pb-3 border-b border-white/10">
        <span className="relative flex h-2.5 w-2.5">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${running ? "bg-emerald-400" : "bg-gray-400"}`} style={{ animationDuration: "2s" }} />
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${running ? "bg-emerald-500" : "bg-gray-500"}`} />
        </span>
        <div className="flex-1">
          <div className="text-[10px] text-muted/50 uppercase tracking-wider leading-tight">Mission</div>
          <div className="text-sm font-bold text-ink">{engine.activeMission?.name || "No Mission"}</div>
        </div>
        <div className="hidden sm:flex items-center gap-6 text-[11px]">
          <div className="text-center">
            <div className="text-muted/50 text-[10px] uppercase">Tick</div>
            <div className="font-mono font-bold text-ink">#{tick}</div>
          </div>
          <div className="text-center">
            <div className="text-muted/50 text-[10px] uppercase">Latency</div>
            <div className="font-mono font-bold text-ink">{(latest("latency") as number).toFixed(2)}ms</div>
          </div>
          <div className="text-center">
            <div className="text-muted/50 text-[10px] uppercase">Safety</div>
            <div className={`font-mono font-bold ${(latest("safetyScore") as number) > 90 ? "text-emerald-600" : "text-amber-600"}`}>{Math.round(latest("safetyScore") as number)}</div>
          </div>
          <div className="text-center">
            <div className="text-muted/50 text-[10px] uppercase">Progress</div>
            <div className="font-mono font-bold text-ink">{Math.round(r.missionProgress)}%</div>
          </div>
          <div className="text-center">
            <div className="text-muted/50 text-[10px] uppercase">Events/s</div>
            <div className="font-mono font-bold text-ink">{Math.round(latest("eventsPerSec") as number)}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-1.5">
        <Bar value={r.battery} label="Battery" color="bg-emerald-500" danger />
        <Bar value={r.cpu} label="CPU" color="bg-blue-500" />
        <Bar value={r.memory} label="Memory" color="bg-violet-500" />
        <Bar value={latest("energyHeadroom") as number} label="Energy Headroom" color="bg-amber-500" />
      </div>
    </div>
  );
}
