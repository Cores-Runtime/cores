"use client";

import { useSimulator } from "./RuntimeContext";

export function MetricsPanel() {
  const { engine } = useSimulator();
  const m = engine.metrics ?? {} as Record<string, number[]>;

  const items = [
    { key: "battery", color: "#202020", label: "Battery" },
    { key: "cpu", color: "#4d4d4d", label: "CPU" },
    { key: "latency", color: "#ff682c", label: "Latency" },
    { key: "safetyScore", color: "#816729", label: "Safety" },
  ];

  return (
    <div>
      <h3 className="font-display text-[12px] tracking-tight text-slate uppercase mb-3">Metrics</h3>
      <div className="grid grid-cols-2 gap-3">
        {items.map(({ key, color, label }) => {
          const data = m[key];
          if (!data || data.length < 2) return null;
          const visible = data.slice(-30);
          const min = Math.min(...visible);
          const max = Math.max(...visible);
          const range = max - min || 1;
          const w = 200; const h = 36;
          const pts = visible.map((v, i) => `${(i / (visible.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
          const cur = visible[visible.length - 1];
          return (
            <div key={key} className="bg-ash rounded-[6px_0px_0px] px-5 py-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-sans text-[11px] text-slate uppercase tracking-wider">{label}</span>
                <span className="font-mono text-[14px] text-graphite tabular-nums">
                  {typeof cur === "number" ? (cur % 1 === 0 ? cur : cur.toFixed(1)) : cur}
                </span>
              </div>
              <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
                <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" />
              </svg>
            </div>
          );
        })}
      </div>
    </div>
  );
}
