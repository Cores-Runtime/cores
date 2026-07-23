"use client";

import { motion } from "framer-motion";

const policies = [
  {
    name: "Priority",
    tag: "Baseline",
    modules: [
      { name: "Navigation", active: true, meta: "P1" },
      { name: "Locomotion", active: true, meta: "P2" },
      { name: "StateEstimation", active: true, meta: "P3" },
      { name: "Perception", active: true, meta: "P4" },
      { name: "Mapping", active: true, meta: "P5" },
    ],
    scores: { safety: 60, mission: 85, energy: 30 },
  },
  {
    name: "Criticality",
    tag: "Safety-First",
    modules: [
      { name: "StateEstimation", active: true, meta: "SIL-4" },
      { name: "Navigation", active: true, meta: "SIL-3" },
      { name: "Locomotion", active: true, meta: "SIL-3" },
      { name: "Perception", active: false, meta: "SIL-2" },
      { name: "Mapping", active: false, meta: "SIL-1" },
    ],
    scores: { safety: 100, mission: 60, energy: 25 },
  },
  {
    name: "Knapsack",
    tag: "Optimized",
    modules: [
      { name: "Navigation", active: true, meta: "36%" },
      { name: "Locomotion", active: true, meta: "24%" },
      { name: "StateEstimation", active: true, meta: "18%" },
      { name: "Perception", active: false, meta: "12%" },
      { name: "Mapping", active: false, meta: "10%" },
    ],
    scores: { safety: 75, mission: 90, energy: 85 },
  },
  {
    name: "Lexicographic",
    tag: "Pareto-Optimal",
    modules: [
      { name: "StateEstimation", active: true, meta: "S1" },
      { name: "Navigation", active: true, meta: "S1" },
      { name: "Locomotion", active: true, meta: "M2" },
      { name: "Mapping", active: true, meta: "M3" },
      { name: "Perception", active: false, meta: "E4" },
    ],
    scores: { safety: 100, mission: 95, energy: 70 },
  },
];

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="font-sans text-[12px] text-slate w-14 shrink-0">{label}</span>
      <div className="flex-1 h-[6px] bg-mist rounded-none overflow-hidden">
        <motion.div
          className="h-full rounded-none"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>
      <span className="font-display text-[14px] tracking-tight text-graphite w-8 text-right tabular-nums">{value}</span>
    </div>
  );
}

export function Policies() {
  return (
    <section id="policies" className="py-[80px] px-6 bg-canvas-white">
      <div className="max-w-page mx-auto">
        <div className="max-w-xl mb-[80px]">
          <span className="font-display text-[13px] tracking-tight text-brass uppercase">
            Scheduling
          </span>
          <h2 className="font-display text-heading-lg leading-heading-lg tracking-heading-lg text-graphite mt-3 max-w-lg">
            One robot. Four policies. Four outcomes.
          </h2>
          <p className="font-sans text-caption leading-caption text-steel mt-3 max-w-md">
            Each policy implements the same trait. Swap it at construction. The runtime never knows the difference.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          {policies.map((policy, i) => (
            <motion.div
              key={policy.name}
              className="card-asymmetric"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="flex items-start justify-between mb-6">
                <div>
                  <span className="font-sans text-[12px] text-brass font-medium">{policy.tag}</span>
                  <h3 className="font-display text-[22px] tracking-tight text-graphite mt-1">{policy.name}</h3>
                </div>
                <span className="font-display text-[14px] tracking-tight text-mist">0{i + 1}</span>
              </div>

              <div className="space-y-[6px] mb-6">
                {policy.modules.map((mod) => (
                  <div key={mod.name} className="flex items-center justify-between py-1.5 border-b border-mist/50 last:border-0">
                    <div className="flex items-center gap-2.5">
                      <span className={`w-[5px] h-[5px] rounded-full shrink-0 ${mod.active ? "bg-graphite" : "bg-mist"}`} />
                      <span className={`font-sans text-[13px] ${mod.active ? "text-graphite" : "text-slate"}`}>
                        {mod.name}
                      </span>
                    </div>
                    <span className="font-mono text-[11px] text-slate">{mod.meta}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-2 pt-5 border-t border-mist">
                <ScoreBar label="Safety" value={policy.scores.safety} color="#ff682c" />
                <ScoreBar label="Mission" value={policy.scores.mission} color="#816729" />
                <ScoreBar label="Energy" value={policy.scores.energy} color="#828282" />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
