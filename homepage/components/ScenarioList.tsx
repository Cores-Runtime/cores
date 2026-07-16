"use client";

import { motion } from "framer-motion";
import { scenarios } from "@/lib/data";
import { useState } from "react";

export function ScenarioList() {
  const [visibleCount, setVisibleCount] = useState(8);
  const allVisible = visibleCount >= scenarios.length;

  return (
    <section 
      id="scenarios" 
      className="py-24 px-6 bg-paper"
      aria-labelledby="scenarios-heading"
    >
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="inline-block px-3 py-1 rounded-full bg-accent/10 text-accent text-sm font-medium mb-4">
            Generated Suite
          </span>
          <h2 id="scenarios-heading" className="text-4xl md:text-5xl font-bold text-ink mb-4 text-balance">
            20 Scenario Types. 50+ Configurations. Seeded Randomization.
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto text-balance">
            Hand-picked scenarios don't generalize. Our generator spans battery, thermal, 
            communication, sensors, actuators, timing, memory, and multi-failure combinations.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {scenarios.slice(0, visibleCount).map((scenario, index) => (
            <motion.div
              key={scenario}
              className="group card p-4 md:p-6 text-left transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: index * 0.02 }}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                  <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-ink group-hover:text-accent transition-colors">
                  {scenario}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {["battery", "thermal", "comms", "sensor", "actuator", "timing", "memory", "multi"].filter(tag => 
                  scenario.toLowerCase().includes(tag) || 
                  (tag === "battery" && (scenario.includes("Battery") || scenario.includes("Thermal"))) ||
                  (tag === "thermal" && scenario.includes("Thermal")) ||
                  (tag === "comms" && (scenario.includes("Communication") || scenario.includes("Network"))) ||
                  (tag === "sensor" && (scenario.includes("Sensor") || scenario.includes("Camera") || scenario.includes("GPS") || scenario.includes("LIDAR"))) ||
                  (tag === "actuator" && scenario.includes("Actuator")) ||
                  (tag === "timing" && (scenario.includes("Deadline") || scenario.includes("Overload"))) ||
                  (tag === "memory" && scenario.includes("Memory")) ||
                  (tag === "multi" && scenario.includes("Multi"))
                ).map((tag, i) => (
                  <span key={i} className="px-2 py-0.5 rounded text-xs font-medium bg-muted/50 text-muted hover:bg-accent/10 hover:text-accent transition-colors">
                    {tag}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {!allVisible && (
          <motion.div
            className="text-center mt-12"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <button
              onClick={() => setVisibleCount(v => Math.min(v + 8, scenarios.length))}
              className="btn-secondary"
            >
              Show {Math.min(visibleCount + 8, scenarios.length)} of {scenarios.length}
            </button>
          </motion.div>
        )}

        <motion.div
          className="mt-12 p-8 card text-center"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h3 className="text-2xl font-bold text-ink mb-4">Monte Carlo Ready</h3>
          <p className="text-muted max-w-xl mx-auto mb-6">
            The same generator powers 1000+ trial Monte Carlo workloads. 
            Seeded randomness means exact reproducibility — same seed, same scenarios, same results.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
            <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
              1000+ Trials
            </span>
            <span className="px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-medium">
              Seeded RNG
            </span>
            <span className="px-3 py-1 rounded-full bg-violet-50 text-violet-700 border border-violet-200 font-medium">
              Exact Reproducibility
            </span>
            <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium">
              CI/CD Ready
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}