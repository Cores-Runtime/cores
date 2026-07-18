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

const typeIcons: Record<string, string> = {
  info: "i",
  warning: "!",
  decision: "→",
  module: "◇",
  success: "✓",
  thinking: "~",
};

export function DecisionTimeline() {
  const { engine } = useSimulator();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [engine.eventHistory.length]);

  const recent = engine.eventHistory.slice(-40);

  return (
    <div className="glass p-5 max-h-[420px] overflow-y-auto">
      <div className="flex items-center justify-between mb-3 sticky top-0 bg-paper/80 backdrop-blur-sm pb-2 z-10">
        <h3 className="text-xs font-bold text-ink uppercase tracking-wider">Event Log</h3>
        <span className="text-[10px] text-muted/50 font-mono">{recent.length} events</span>
      </div>
      <div className="space-y-0.5">
        {recent.map((entry, i) => (
          <div key={i} className={`flex items-start gap-2 p-1.5 rounded border-l-[3px] text-[11px] ${typeStyles[entry.type] || typeStyles.info}`}>
            <span className="w-4 h-4 rounded flex items-center justify-center text-[9px] font-bold shrink-0 mt-0.5 bg-white/60 text-muted/60 font-mono">{typeIcons[entry.type] || "•"}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-mono text-muted/50">T{entry.tick}</span>
                <span className={`text-[9px] font-medium uppercase ${entry.type === "warning" ? "text-amber-600" : entry.type === "success" ? "text-emerald-600" : entry.type === "decision" ? "text-violet-600" : "text-muted/50"}`}>{entry.type}</span>
              </div>
              <div className="text-[11px] text-ink/80 leading-snug">{entry.event}</div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
