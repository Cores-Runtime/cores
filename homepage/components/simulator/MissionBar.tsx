"use client";

import { useSimulator } from "./RuntimeContext";

export function MissionBar() {
  const { engine, tick, running, mode } = useSimulator();
  const r = engine.robot;
  const m = engine.metrics;

  const latest = (key: string) => {
    const arr = m[key];
    return arr && arr.length > 0 ? arr[arr.length - 1] : 0;
  };

  return (
    <div className="bg-ash rounded-[6px_0px_0px] px-8 py-5">
      <div className="flex items-center gap-6 mb-4">
        <span className={`w-2 h-2 rounded-full shrink-0 ${running ? "bg-ember-orange" : "bg-mist"}`} />
        <div className="flex-1 min-w-0">
          <span className="font-sans text-[11px] text-slate uppercase tracking-wider">Mission</span>
          <span className="font-display text-[15px] tracking-tight text-graphite ml-3">
            {engine.activeMission?.name || "No Mission"}
          </span>
        </div>
        <div className="flex items-center gap-5 text-[12px]">
          <div className="text-center">
            <div className="font-sans text-[10px] text-slate uppercase tracking-wider">Tick</div>
            <div className="font-mono text-[13px] text-graphite tabular-nums">#{tick}</div>
          </div>
          <div className="text-center">
            <div className="font-sans text-[10px] text-slate uppercase tracking-wider">Latency</div>
            <div className="font-mono text-[13px] text-graphite tabular-nums">{(latest("latency") as number).toFixed(1)}ms</div>
          </div>
          <div className="text-center">
            <div className="font-sans text-[10px] text-slate uppercase tracking-wider">Safety</div>
            <div className={`font-mono text-[13px] tabular-nums ${(latest("safetyScore") as number) > 90 ? "text-ember-orange" : "text-brass"}`}>
              {Math.round(latest("safetyScore") as number)}
            </div>
          </div>
          <div className="text-center">
            <div className="font-sans text-[10px] text-slate uppercase tracking-wider">Progress</div>
            <div className="font-mono text-[13px] text-graphite tabular-nums">{Math.round(r.missionProgress)}%</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { value: r.battery, label: "Battery", threshold: 25 },
          { value: r.cpu, label: "CPU", threshold: 85 },
          { value: r.memory, label: "Memory", threshold: 85 },
          { value: latest("energyHeadroom") as number, label: "Headroom", threshold: 20 },
        ].map(({ value, label, threshold }) => {
          const pct = Math.min(100, Math.max(0, value));
          const danger = pct < threshold;
          return (
            <div key={label} className="flex items-center gap-2">
              <span className="font-sans text-[11px] text-slate w-16 shrink-0">{label}</span>
              <div className="flex-1 h-[6px] bg-mist rounded-none overflow-hidden">
                <div
                  className="h-full rounded-none bg-graphite transition-all duration-500"
                  style={{ width: `${pct}%`, backgroundColor: danger ? "#ff682c" : "#202020" }}
                />
              </div>
              <span className="font-mono text-[11px] text-graphite w-8 text-right tabular-nums">{Math.round(pct)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
