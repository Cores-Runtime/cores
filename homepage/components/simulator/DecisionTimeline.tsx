"use client";

import { useRef, useEffect } from "react";
import { useSimulator } from "./RuntimeContext";

const typeDots: Record<string, string> = {
  info: "bg-graphite",
  warning: "bg-ember-orange",
  decision: "bg-brass",
  module: "bg-steel",
  success: "bg-graphite",
  thinking: "bg-slate",
};

export function DecisionTimeline() {
  const { engine } = useSimulator();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [engine.eventHistory.length]);

  const recent = engine.eventHistory.slice(-40);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-display text-[12px] tracking-tight text-slate uppercase">Event Log</h3>
        <span className="font-sans text-[11px] text-slate tabular-nums">{recent.length} events</span>
      </div>
      <div className="bg-ash rounded-[6px_0px_0px] px-6 py-5 max-h-[360px] overflow-y-auto">
        <div className="space-y-[2px]">
          {recent.map((entry, i) => (
            <div key={i} className="flex items-start gap-3 py-1.5 border-b border-mist/50 last:border-0">
              <span className={`w-[5px] h-[5px] rounded-full shrink-0 mt-1.5 ${typeDots[entry.type] || typeDots.info}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-sans text-[10px] text-slate tabular-nums">T{entry.tick}</span>
                  <span className="font-sans text-[10px] text-slate uppercase tracking-wider">{entry.type}</span>
                </div>
                <div className="font-sans text-[12px] text-graphite leading-snug mt-0.5">{entry.event}</div>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
