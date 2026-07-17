"use client";

import { useRef, useEffect } from "react";
import { useSimulator } from "./RuntimeContext";

const typeStyles: Record<string, string> = {
  info: "border-l-blue-400 bg-blue-50/30",
  warning: "border-l-amber-400 bg-amber-50/30",
  decision: "border-l-violet-400 bg-violet-50/30",
  module: "border-l-emerald-400 bg-emerald-50/30",
  success: "border-l-green-400 bg-green-50/30",
  thinking: "border-l-amber-400 bg-amber-50/20",
};
const dotColors: Record<string, string> = {
  info: "bg-blue-500", warning: "bg-amber-500", decision: "bg-violet-500",
  module: "bg-emerald-500", success: "bg-green-500", thinking: "bg-amber-500",
};

export function DecisionTimeline() {
  const { engine } = useSimulator();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [engine.timeline.length]);

  const recent = engine.timeline.slice(-30);

  return (
    <div className="glass p-5 max-h-[360px] overflow-y-auto scrollbar-hide">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-3 sticky top-0 bg-paper/80 backdrop-blur-sm pb-2 z-10">Decision Timeline</h3>
      <div className="space-y-1">
        {recent.map((entry, i) => (
          <div key={i} className={`flex items-start gap-2.5 p-2 rounded border-l-2 ${typeStyles[entry.type] || typeStyles.info}`}>
            <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${dotColors[entry.type]}`} />
            <div className="min-w-0">
              <span className="text-[10px] font-mono text-muted/50">T{entry.tick}</span>
              <div className="text-[11px] text-ink font-medium">{entry.event}</div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
