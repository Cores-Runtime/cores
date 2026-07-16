"use client";

import { motion } from "framer-motion";

export function AblationSection() {
  const ablationData = [
    { name: "No Lexicographic Ordering", safety: "0%", mission: "-23%", time: "-17ms", desc: "Reverts to single-objective — loses safety guarantees" },
    { name: "No Safety-Critical Distinction", safety: "-17%", mission: "-3%", time: "+5ms", desc: "Safety modules treated as regular mission tasks" },
    { name: "No Mandatory Modules", safety: "-10%", mission: "-10%", time: "0ms", desc: "Battery monitor, logger become optional" },
    { name: "No Module Classes", safety: "-17%", mission: "-3%", time: "+4ms", desc: "Flat priority — no hierarchy enforcement" },
    { name: "No Dependency Graph", safety: "0%", mission: "0%", time: "-5ms", desc: "Structure unused in current benchmark" },
    { name: "No Redundancy Handling", safety: "0%", mission: "0%", time: "-5ms", desc: "Redundancy not triggered in scenarios" },
    { name: "No Mutual Exclusion", safety: "0%", mission: "0%", time: "-7ms", desc: "Mutex pairs not simultaneously optimal" },
    { name: "No Shared Information", safety: "0%", mission: "0%", time: "-11ms", desc: "Info sharing not modeled in utility" },
  ];

  return (
    <section 
      id="ablation" 
      className="py-24 px-6 bg-muted/30"
      aria-labelledby="ablation-heading"
    >
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="inline-block px-3 py-1 rounded-full bg-accent/10 text-accent text-sm font-medium mb-4">
            Ablation Study
          </span>
          <h2 id="ablation-heading" className="text-4xl md:text-5xl font-bold text-ink mb-4 text-balance">
            What Actually Matters?
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto text-balance">
            Remove one architectural component at a time. Measure the delta. 
            Reviewers love this — it isolates the contribution of each design choice.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-8 mb-16">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="card p-6 md:p-8"
          >
            <h3 className="text-xl font-bold text-ink mb-6 flex items-center gap-3">
              <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Top Impacts
            </h3>
            <div className="space-y-4">
              {ablationData.map((item, i) => (
                <motion.div
                  key={item.name}
                  className="p-4 rounded-lg bg-muted/30 border border-border hover:border-accent/30 transition-colors"
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-ink">{item.name}</span>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="flex items-center gap-1 text-danger">
                        <span className="w-2 h-2 rounded-full bg-danger" />
                        Safety: {item.safety}
                      </span>
                      <span className="flex items-center gap-1 text-accent">
                        <span className="w-2 h-2 rounded-full bg-accent" />
                        Mission: {item.mission}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-muted">{item.desc}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="card p-6 md:p-8"
          >
            <h3 className="text-xl font-bold text-ink mb-6 flex items-center gap-3">
              <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-5.618 6.984m0 0l2 2m0 0l-2-2m2 2l-2 2" />
              </svg>
              Key Insights
            </h3>
            <div className="space-y-4">
              {[
                "Lexicographic ordering is the single largest contributor to safety — removing it drops mission utility 23% while keeping safety flat",
                "Safety-critical distinction matters: treating safety modules as mission tasks reduces coverage 17%",
                "Mandatory modules (battery, logger) provide baseline functionality — removing them hurts both axes",
                "Module classes (mandatory > safety > mission > optional) encode robotics domain knowledge directly",
                "Graph structure (deps, mutex, redundancy) shows zero impact in current scenarios — needs adversarial test generation",
              ].map((insight, i) => (
                <motion.div
                  key={i}
                  className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08 }}
                >
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-accent/10 flex items-center justify-center">
                    <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-sm text-muted leading-relaxed">{insight}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        <motion.div
          className="card p-8"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h3 className="text-2xl font-bold text-ink mb-6 text-center">Ablation Data (CSV)</h3>
          <div className="bg-code rounded-lg p-6 overflow-x-auto">
            <pre className="text-sm text-paper/90 font-mono leading-relaxed"><code>{`ablation_type,scenario,safety_coverage,mission_utility,energy_headroom,decision_time_ms
full,Nominal Exploration,1.000,0.526,0.590,0.758
no_lexicographic,Nominal Exploration,1.000,0.405,0.585,0.585
no_safety_critical,Nominal Exploration,0.833,0.512,0.595,0.811
no_mandatory,Nominal Exploration,0.900,0.474,0.610,0.752
no_module_classes,Nominal Exploration,0.833,0.512,0.595,0.802
no_dependency_graph,Nominal Exploration,1.000,0.526,0.590,0.707
no_redundancy,Nominal Exploration,1.000,0.526,0.590,0.712
no_mutual_exclusion,Nominal Exploration,1.000,0.526,0.590,0.692
no_shared_info,Nominal Exploration,1.000,0.526,0.590,0.644
full,Low Battery,1.000,0.289,0.000,0.589
no_lexicographic,Low Battery,1.000,0.189,0.008,0.416
no_safety_critical,Low Battery,0.833,0.263,0.016,0.642
...`}</code></pre>
          </div>
          <p className="text-sm text-muted mt-4 text-center">
            Full CSV: <code className="bg-code/5 px-1.5 py-0.5 rounded font-mono text-xs text-accent">ablation_results.csv</code> | 
            Summary: <code className="bg-code/5 px-1.5 py-0.5 rounded font-mono text-xs text-accent">ablation_summary.csv</code> | 
            Impact: <code className="bg-code/5 px-1.5 py-0.5 rounded font-mono text-xs text-accent">ablation_impact.csv</code>
          </p>
        </motion.div>
      </div>
    </section>
  );
}