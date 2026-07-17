"use client";

import { useSimulator } from "./RuntimeContext";

function MiniChart({ data, color, label, unit }: { data: readonly number[]; color: string; label: string; unit: string }) {
  const visible = data.slice(-20);
  if (visible.length < 2) return null;
  const min = Math.min(...visible);
  const max = Math.max(...visible);
  const range = max - min || 1;
  const w = 80; const h = 28;
  const pts = visible.map((v, i) => `${(i / (visible.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  const cur = visible[visible.length - 1];

  return (
    <div>
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-[10px] text-muted/50">{label}</span>
        <span className="text-[11px] font-bold text-ink">{typeof cur === "number" ? (cur % 1 === 0 ? cur : cur.toFixed(1)) : cur}{unit}</span>
      </div>
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="w-full">
        <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={w} cy={h - ((cur - min) / range) * h} r="2" fill={color} />
      </svg>
    </div>
  );
}

export function MetricsPanel() {
  const { engine } = useSimulator();
  const m = engine.metrics;

  return (
    <div className="glass p-5 col-span-full">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-4">Live Metrics</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {m.battery.length > 1 && <MiniChart data={m.battery} color="#10B981" label="Battery" unit="%" />}
        {m.cpu.length > 1 && <MiniChart data={m.cpu} color="#3B82F6" label="CPU" unit="%" />}
        {m.memory.length > 1 && <MiniChart data={m.memory} color="#8B5CF6" label="Memory" unit="%" />}
        {m.latency.length > 1 && <MiniChart data={m.latency} color="#F59E0B" label="Latency" unit="ms" />}
        {m.missionUtility.length > 1 && <MiniChart data={m.missionUtility} color="#10B981" label="Mission Utility" unit="%" />}
        {m.safetyScore.length > 1 && <MiniChart data={m.safetyScore} color="#EF4444" label="Safety Score" unit="%" />}
        {m.energyHeadroom.length > 1 && <MiniChart data={m.energyHeadroom} color="#F59E0B" label="Energy Headroom" unit="%" />}
        {m.eventsPerSec.length > 1 && <MiniChart data={m.eventsPerSec} color="#3B82F6" label="Events/sec" unit="" />}
      </div>
    </div>
  );
}
