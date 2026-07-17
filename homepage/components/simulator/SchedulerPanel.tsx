"use client";

import { useSimulator } from "./RuntimeContext";

export function SchedulerPanel() {
  const { engine } = useSimulator();
  const d = engine.decision;

  return (
    <div className="glass p-5">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-3">Scheduler</h3>

      <div className="flex items-center gap-2 mb-3 pb-3 border-b border-white/10">
        <span className="text-[10px] text-muted/50 uppercase">Policy</span>
        <span className="text-sm font-bold text-accent">Lexicographic</span>
        <span className="ml-auto text-[10px] text-muted/50">{d ? d.decisionTimeMs.toFixed(2) : "0.00"} ms</span>
      </div>

      <div className="space-y-1 mb-4">
        <div className="text-[10px] text-muted/50 uppercase mb-1.5">Priority Chain</div>
        {(d?.hierarchy || ["Safety", "Mission", "Energy", "Memory"]).map((h, i) => (
          <div key={h} className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${i === 0 ? "bg-red-500" : i === 1 ? "bg-blue-500" : i === 2 ? "bg-amber-500" : "bg-violet-500"}`} />
            <div className="flex-1 h-5 rounded bg-white/40 border border-white/10 relative overflow-hidden">
              <div className="absolute inset-y-0 left-0 rounded bg-accent/10 transition-all" style={{ width: `${i === 0 ? 100 : 100 - i * 20}%` }} />
            </div>
            <span className="text-[11px] font-medium text-ink w-16 text-right">{h}</span>
          </div>
        ))}
      </div>

      {d && (
        <div className="p-3 rounded-lg bg-amber-50/50 border border-amber-200/30">
          <div className="text-[10px] font-bold text-amber-700 uppercase mb-1">Decision</div>
          <div className="text-xs font-medium text-ink mb-1 leading-snug">
            {d.wake.length > 0 && `Wake: ${d.wake.join(", ")}`}
            {d.suspend.length > 0 && ` | Suspend: ${d.suspend.join(", ")}`}
          </div>
          <div className="text-[11px] text-muted/70 leading-relaxed">{d.reason}</div>
        </div>
      )}
    </div>
  );
}
