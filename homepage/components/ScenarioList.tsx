"use client";

import { motion } from "framer-motion";
import { scenarios } from "@/lib/data";

const legend = [
  { label: "Power", color: "bg-ember-orange" },
  { label: "Thermal", color: "bg-brass" },
  { label: "Comms", color: "bg-slate" },
  { label: "Sensor", color: "bg-steel" },
  { label: "Actuator", color: "bg-graphite" },
  { label: "Timing", color: "bg-mist" },
];

export function ScenarioList() {
  return (
    <section id="scenarios" className="py-[80px] px-6 bg-ash">
      <div className="max-w-page mx-auto">
        <div className="grid lg:grid-cols-5 gap-16 mb-[80px]">
          <div className="lg:col-span-2">
            <span className="font-display text-[13px] tracking-tight text-brass uppercase">
              Test Suite
            </span>
            <h2 className="font-display text-heading-lg leading-heading-lg tracking-heading-lg text-graphite mt-3">
              Failure is the input.
            </h2>
            <p className="font-sans text-caption leading-caption text-steel mt-3">
              Twenty scenario families. Deterministic seeds. Every cycle is a new failure mode vector.
            </p>
            <p className="font-sans text-[14px] text-slate mt-4 leading-relaxed">
              Hand-picked scenarios do not generalize. This generator spans every subsystem, then combines them. The same code drives 1000+ trial Monte Carlo workloads.
            </p>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 mt-8">
              {legend.map((d) => (
                <span key={d.label} className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-none ${d.color}`} />
                  <span className="font-sans text-[12px] text-slate">{d.label}</span>
                </span>
              ))}
            </div>
          </div>

          <div className="lg:col-span-3">
            <div className="grid grid-cols-2 gap-2">
              {scenarios.map((scenario, i) => {
                const severity = Math.sin(i * 1.7) * 0.5 + 0.5;
                return (
                  <motion.div
                    key={scenario}
                    className="bg-canvas-white rounded-[4px_0px_0px] px-4 py-3 flex items-center gap-3"
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.025 }}
                  >
                    <span className="font-display text-[13px] tracking-tight text-slate w-5 text-right shrink-0 tabular-nums">
                      {i + 1}
                    </span>
                    <span className="font-sans text-[13px] text-graphite leading-snug flex-1">
                      {scenario}
                    </span>
                    <div className="flex gap-1 shrink-0">
                      {legend.slice(0, 3).map((d) => (
                        <span
                          key={d.label}
                          className={`w-[5px] h-[5px] rounded-none ${severity > 0.5 ? d.color : "bg-mist"}`}
                        />
                      ))}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>

        <motion.div
          className="bg-ivory rounded-[6px_0px_0px] px-12 py-10 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="max-w-lg mx-auto">
            <h3 className="font-display text-[20px] tracking-tight text-graphite mb-3">
              Monte Carlo Mode
            </h3>
            <p className="font-sans text-[14px] text-steel leading-relaxed">
              The same ScenarioGenerator feeds 1000+ trial Monte Carlo workloads. Seeded RNG guarantees exact reproducibility.
            </p>
            <div className="flex items-center justify-center gap-8 mt-6">
              <div className="text-left">
                <div className="font-display text-[36px] tracking-tight text-graphite tabular-nums">1000+</div>
                <div className="font-sans text-[12px] text-slate mt-0.5">Trials</div>
              </div>
              <div className="w-px h-9 bg-mist" />
              <div className="text-left">
                <div className="font-display text-[36px] tracking-tight text-graphite tabular-nums">100%</div>
                <div className="font-sans text-[12px] text-slate mt-0.5">Reproducible</div>
              </div>
              <div className="w-px h-9 bg-mist" />
              <div className="text-left">
                <div className="font-display text-[36px] tracking-tight text-graphite tabular-nums">20</div>
                <div className="font-sans text-[12px] text-slate mt-0.5">Seeds</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
