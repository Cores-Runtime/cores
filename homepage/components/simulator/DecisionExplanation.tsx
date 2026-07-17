"use client";

import { useSimulator } from "./RuntimeContext";

export function DecisionExplanation() {
  const { engine } = useSimulator();
  const d = engine.decision;
  if (!d) return null;

  const steps: string[] = [];
  if (d.reason) steps.push(d.reason);
  for (const id of d.wake) {
    const def = engine.getModuleDef(id);
    steps.push(`${def?.name || id} activated for ${d.priority.toLowerCase()} priority`);
  }
  for (const id of d.suspend) {
    const def = engine.getModuleDef(id);
    steps.push(`${def?.name || id} suspended — CPU reallocated`);
  }
  steps.push(`${d.priority} priority enforced`);

  return (
    <div className="glass p-5 col-span-full">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-3">Why?</h3>
      <div className="flex flex-wrap items-start gap-1">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/40 border border-white/10">
              <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
              <span className="text-ink/80">{step}</span>
            </div>
            {i < steps.length - 1 && (
              <svg className="w-4 h-4 text-muted/30 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
