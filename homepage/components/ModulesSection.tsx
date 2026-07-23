"use client";

import { motion } from "framer-motion";

const layers = [
  {
    num: "04",
    name: "Lexicographic Scheduler",
    desc: "Multi-objective dispatch across safety, mission, and energy dimensions. Produces the one Pareto-optimal execution plan for each cycle.",
    stat: "3 objectives",
    detail: "Safety > Mission > Energy",
  },
  {
    num: "03",
    name: "Risk-Aware Knapsack",
    desc: "Energy-budgeted task selection modeled as a knapsack problem. Maximizes mission value within the available energy envelope.",
    stat: "<1ms solve",
    detail: "Value-weighted selection",
  },
  {
    num: "02",
    name: "Criticality Scheduling",
    desc: "Safety-critical modules receive bounded, non-preemptible execution slots with SIL-4 equivalent fault containment.",
    stat: "SIL-4",
    detail: "Zero cross-criticality interference",
  },
  {
    num: "01",
    name: "Runtime Foundation",
    desc: "Deterministic priority scheduler with O(1) dispatch and zero-allocation hot paths. Fixed-priority preemptive scheduling.",
    stat: "O(1)",
    detail: "No GC. No surprises.",
  },
];

export function ModulesSection() {
  return (
    <section id="modules" className="py-[80px] px-6 bg-ash">
      <div className="max-w-page mx-auto">
        <div className="max-w-xl mb-[80px]">
          <span className="font-display text-[13px] tracking-tight text-brass uppercase">
            Architecture
          </span>
          <h2 className="font-display text-heading-lg leading-heading-lg tracking-heading-lg text-graphite mt-3 max-w-lg">
            The stack is the interface.
          </h2>
          <p className="font-sans text-caption leading-caption text-steel mt-3 max-w-md">
            Modules compose vertically. Each layer adds intelligence without breaking determinism. The runtime never knows which modules are loaded.
          </p>
        </div>

        <div className="relative">
          {layers.map((layer, i) => (
            <motion.div
              key={layer.num}
              className="relative z-10 mb-3 last:mb-0"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <div className="card-data flex items-center gap-8">
                <span className="font-display text-[48px] leading-none tracking-tight text-mist shrink-0 w-[72px] tabular-nums">
                  {layer.num}
                </span>
                <div className="flex-1 min-w-0">
                  <h3 className="font-display text-[18px] tracking-tight text-graphite">
                    {layer.name}
                  </h3>
                  <p className="font-sans text-[14px] text-steel mt-1.5 leading-relaxed max-w-xl">
                    {layer.desc}
                  </p>
                </div>
                <div className="text-right shrink-0 hidden md:block">
                  <div className="font-display text-[13px] tracking-tight text-brass uppercase">
                    {layer.stat}
                  </div>
                  <div className="font-sans text-[12px] text-slate mt-0.5">
                    {layer.detail}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}

          <motion.div
            className="relative z-0 -mt-3"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
          >
            <div className="bg-graphite rounded-[6px_0px_0px] px-10 py-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="font-display text-[24px] leading-none tracking-tight text-ash/50">CR</span>
                <span className="font-display text-[16px] tracking-tight text-canvas-white">CORES Runtime</span>
              </div>
              <span className="font-sans text-[13px] text-canvas-white/60">Deterministic cycle · 128 μs avg</span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
