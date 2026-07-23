"use client";

import { motion } from "framer-motion";

const metrics = [
  {
    label: "Tasks Scheduled",
    value: "12,847",
    delta: "+4.2%",
    trend: [30, 45, 38, 52, 48, 55, 62, 58, 65, 70, 68, 72],
  },
  {
    label: "Avg Latency",
    value: "128 μs",
    delta: "-3.1%",
    trend: [140, 135, 130, 128, 125, 130, 128, 126, 124, 122, 120, 118],
  },
  {
    label: "Safety Violations",
    value: "0",
    delta: "0%",
    trend: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  },
  {
    label: "Energy Efficiency",
    value: "87%",
    delta: "+2.5%",
    trend: [75, 78, 80, 82, 83, 84, 85, 85, 86, 86, 87, 87],
  },
];

const cycles = Array.from({ length: 81 }, (_, i) => ({
  cycle: i,
  modules: 3 + Math.floor(Math.sin(i * 0.3) * 2 + 1),
  battery: Math.max(0, 100 - i * 1.2),
  critical: i > 20 && i < 40 ? 1 : 0,
}));

function Sparkline({ data, color = "#ff682c" }: { data: number[]; color?: string }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 200;
  const h = 36;
  const points = data
    .map((d, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((d - min) / range) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-9">
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
    </svg>
  );
}

export function Visualizations() {
  return (
    <section id="visualizations" className="py-[80px] px-6 bg-canvas-white">
      <div className="max-w-page mx-auto">
        <div className="max-w-xl mb-[80px]">
          <span className="font-display text-[13px] tracking-tight text-brass uppercase">
            Telemetry
          </span>
          <h2 className="font-display text-heading-lg leading-heading-lg tracking-heading-lg text-graphite mt-3 max-w-lg">
            Every cycle, measured.
          </h2>
          <p className="font-sans text-caption leading-caption text-steel mt-3 max-w-md">
            Deterministic execution produces deterministic traces. Every tick is logged, measured, and accountable.
          </p>
        </div>

        <div className="grid md:grid-cols-4 gap-5 mb-10">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              className="card-asymmetric"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="flex items-center justify-between mb-4">
                <span className="font-sans text-[12px] text-slate">{m.label}</span>
                <span className="font-sans text-[11px] text-slate">{m.delta}</span>
              </div>
              <div className="font-display text-[36px] tracking-tight text-graphite tabular-nums mb-4">
                {m.value}
              </div>
              <Sparkline data={m.trend} color={i === 2 ? "#816729" : "#ff682c"} />
            </motion.div>
          ))}
        </div>

        <motion.div
          className="card-asymmetric"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-display text-[16px] tracking-tight text-graphite">Runtime Cycle Trace</h3>
            <span className="font-sans text-[12px] text-slate">81 ticks</span>
          </div>

          <div className="overflow-x-auto pb-2">
            <div className="flex gap-[3px] min-w-[700px]">
              {cycles.map((c) => (
                <div key={c.cycle} className="flex flex-col items-center gap-1 flex-1">
                  <div className="relative w-full h-24 flex flex-col justify-end">
                    <div
                      className="w-full bg-steel/10 rounded-[1px] transition-all"
                      style={{ height: `${(c.modules / 6) * 100}%` }}
                    />
                    <div
                      className="w-full bg-ember-orange/20 rounded-[1px] transition-all mt-[2px]"
                      style={{ height: `${(c.battery / 100) * 20}px` }}
                    />
                    {c.critical > 0 && (
                      <div className="absolute top-0 left-0 right-0 h-[3px] bg-ember-orange rounded-[1px]" />
                    )}
                  </div>
                  {c.cycle % 10 === 0 && (
                    <span className="font-sans text-[10px] text-slate mt-1 tabular-nums">{c.cycle}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-6 mt-6 pt-6 border-t border-mist">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 bg-steel/10 rounded-[1px]" />
              <span className="font-sans text-[12px] text-slate">Active modules</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 bg-ember-orange/20 rounded-[1px]" />
              <span className="font-sans text-[12px] text-slate">Battery</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="w-[3px] h-3 bg-ember-orange rounded-[1px]" />
              <span className="font-sans text-[12px] text-slate">Critical event</span>
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
