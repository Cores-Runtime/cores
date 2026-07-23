"use client";

import { useSimulator } from "./RuntimeContext";

export function SchedulerPanel() {
  const { engine } = useSimulator();
  const d = engine.decision;

  const steps: string[] = [];
  if (d) {
    if (d.reason) steps.push(d.reason);
    for (const id of d.wake) {
      const def = engine.getModuleDef(id);
      steps.push(`${def?.name || id} activated`);
    }
    for (const id of d.suspend) {
      const def = engine.getModuleDef(id);
      steps.push(`${def?.name || id} suspended`);
    }
    steps.push(`${d.priority} priority enforced`);
  }

  return (
    <div>
      <h3 className="font-display text-[12px] tracking-tight text-slate uppercase mb-3">Scheduler</h3>
      <div className="bg-ash rounded-[6px_0px_0px] px-6 py-5 space-y-4">
        <div className="flex items-center justify-between">
          <span className="font-sans text-[11px] text-slate uppercase tracking-wider">Policy</span>
          <span className="font-display text-[14px] tracking-tight text-graphite">Lexicographic</span>
          <span className="font-mono text-[11px] text-slate tabular-nums">{d ? d.decisionTimeMs.toFixed(2) : "0.00"}ms</span>
        </div>

        {(d?.hierarchy || ["Safety", "Mission", "Energy", "Memory"]).map((h, i) => (
          <div key={h} className="flex items-center gap-2">
            <span className={`w-[5px] h-[5px] rounded-full shrink-0 ${
              i === 0 ? "bg-ember-orange" : i === 1 ? "bg-brass" : i === 2 ? "bg-slate" : "bg-mist"
            }`} />
            <div className="flex-1 h-[6px] bg-mist rounded-none overflow-hidden">
              <div className="h-full rounded-none bg-graphite/20 transition-all" style={{ width: `${100 - i * 20}%` }} />
            </div>
            <span className="font-sans text-[11px] text-graphite w-16 text-right">{h}</span>
          </div>
        ))}

        {steps.length > 0 && (
          <div className="pt-3 border-t border-mist space-y-2">
            <span className="font-sans text-[10px] text-slate uppercase tracking-wider block">Why</span>
            <div className="space-y-1.5">
              {steps.map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-[5px] h-[5px] rounded-full bg-graphite shrink-0 mt-1.5" />
                  <span className="font-sans text-[12px] text-steel leading-relaxed">{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
