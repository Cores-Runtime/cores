"use client";

import { useSimulator } from "./RuntimeContext";

function Sparkline({ data, color, label, unit }: { data: readonly number[]; color: string; label: string; unit: string }) {
  const visible = data.slice(-30);
  if (visible.length < 2) return null;
  const min = Math.min(...visible);
  const max = Math.max(...visible);
  const range = max - min || 1;
  const w = 200; const h = 50;
  const pts = visible.map((v, i) => `${(i / (visible.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  const cur = visible[visible.length - 1];

  return (
    <div className="p-3 rounded-lg bg-white/40 border border-white/10">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] text-muted/50 uppercase tracking-wider">{label}</span>
        <span className="text-xs font-bold font-mono text-ink">{typeof cur === "number" ? (cur % 1 === 0 ? cur : cur.toFixed(1)) : cur}<span className="text-muted/50 text-[10px] ml-0.5">{unit}</span></span>
      </div>
      <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="overflow-visible">
        <defs>
          <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.15" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={w} cy={h - ((cur - min) / range) * h} r="2.5" fill={color} stroke="white" strokeWidth="1" />
      </svg>
    </div>
  );
}

export function MetricsPanel() {
  const { engine } = useSimulator();
  const m = engine.metrics ?? {} as Record<string, number[]>;

  const spark = (key: string, color: string, label: string, unit: string) => {
    const data = m[key];
    if (!data || data.length < 2) return null;
    return <Sparkline data={data} color={color} label={label} unit={unit} />;
  };

  return (
    <div className="glass p-5">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-3">Live Metrics</h3>
      <div className="grid grid-cols-2 gap-2">
        {spark("battery", "#10B981", "Battery", "%")}
        {spark("cpu", "#3B82F6", "CPU", "%")}
        {spark("memory", "#8B5CF6", "Memory", "%")}
        {spark("latency", "#F59E0B", "Latency", "ms")}
        {spark("missionUtility", "#10B981", "Utility", "%")}
        {spark("safetyScore", "#EF4444", "Safety", "%")}
        {spark("energyHeadroom", "#F59E0B", "Headroom", "%")}
        {spark("eventsPerSec", "#3B82F6", "Events/s", "")}
      </div>
    </div>
  );
}
