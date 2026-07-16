"use client";

import { motion } from "framer-motion";

const modules = [
  {
    name: "Runtime Foundation",
    desc: "Deterministic task scheduling with priority-based dispatch. Zero-allocation hot path. No GC pauses.",
    color: "emerald",
    items: ["Priority scheduler", "Task lifecycle management", "Resource budgeting"],
  },
  {
    name: "Criticality Scheduling",
    desc: "Safety-critical task isolation with bounded slack. SIL-4 equivalent partitioning.",
    color: "blue",
    items: ["Safety level classification", "Bounded execution slots", "Fault containment"],
  },
  {
    name: "Risk-Aware Knapsack",
    desc: "Energy-aware optimization under variable budgets. Knapsack selection over mission value.",
    color: "violet",
    items: ["Budget-aware task selection", "Energy headroom tracking", "Mission value scoring"],
  },
  {
    name: "Lexicographic Scheduler",
    desc: "Multi-objective Pareto-optimal dispatch. Safety first, then mission, then energy.",
    color: "amber",
    items: ["Lexicographic ordering", "Pareto frontier analysis", "Deterministic output"],
  },
];

export function ModulesSection() {
  return (
    <section id="modules" className="py-24 px-6 bg-paper">
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="inline-block px-3 py-1 rounded-full bg-accent/10 text-accent text-sm font-medium mb-4">
            Architecture
          </span>
          <h2 className="text-4xl md:text-5xl font-bold text-ink mb-4 text-balance">
            Core Modules
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto text-balance">
            Four composable modules that build on each other. Each adds a layer of
            intelligence without compromising determinism.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {modules.map((mod, i) => (
            <motion.div
              key={mod.name}
              className="card p-8"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <div className={`w-10 h-10 rounded-lg bg-${mod.color}-500/10 flex items-center justify-center mb-4`}>
                <div className={`w-3 h-3 rounded-full bg-${mod.color}-500`} />
              </div>
              <h3 className="text-xl font-bold text-ink mb-2">{mod.name}</h3>
              <p className="text-muted mb-4">{mod.desc}</p>
              <ul className="space-y-1">
                {mod.items.map(item => (
                  <li key={item} className="text-sm text-muted/70 flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full bg-${mod.color}-500 shrink-0`} />
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
