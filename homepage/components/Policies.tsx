"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { policies } from "@/lib/data";

export function Policies() {
  return (
    <section 
      id="policies" 
      className="py-24 px-6 bg-muted/30"
      aria-labelledby="policies-heading"
    >
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="inline-block px-3 py-1 rounded-full bg-accent/10 text-accent text-sm font-medium mb-4">
            Policy Comparison
          </span>
          <h2 id="policies-heading" className="text-4xl md:text-5xl font-bold text-ink mb-4 text-balance">
            Four Policies. One Interface.
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto text-balance">
            The <code className="bg-code/5 px-1.5 py-0.5 rounded font-mono text-xs text-accent">SchedulingPolicy</code> abstraction 
            lets you swap scheduling intelligence without touching the runtime.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {policies.map((policy, index) => (
            <motion.article
              key={policy.name}
              className="group relative card p-6 md:p-8 flex flex-col"
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
            >
              <div className="flex items-center gap-3 mb-4">
                <span className={`px-3 py-1 rounded-full text-xs font-medium border ${policy.color} text-ink bg-paper border-2`}>
                  {policy.badge}
                </span>
                <span className="px-2 py-1 rounded-full text-xs font-medium bg-ink/5 text-ink/70 border border-border">
                  {policy.type}
                </span>
              </div>

              <h3 className="text-xl font-bold text-ink mb-3 group-hover:text-accent transition-colors">
                {policy.name}
              </h3>

              <p className="text-muted text-sm mb-6 flex-1 group-hover:text-ink/80 transition-colors">
                {policy.description.replace(/—/g, " - ")}
              </p>

              <div className="pt-4 border-t border-border">
                <div className="flex items-center gap-2 text-xs text-muted mb-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Deterministic
                </div>
                <div className="flex items-center gap-2 text-xs text-muted mb-2">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  Synchronous
                </div>
                <div className="flex items-center gap-2 text-xs text-muted">
                  <span className="w-2 h-2 rounded-full bg-violet-500" />
                  Pure Functions
                </div>
              </div>

              <Link 
                href="#" 
                className="mt-6 inline-flex items-center gap-2 text-accent font-medium text-sm group-hover:gap-3 transition-all opacity-0 group-hover:opacity-100"
              >
                Implementation Details
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </Link>
            </motion.article>
          ))}
        </div>

        <motion.div
          className="mt-16 p-8 card"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h3 className="text-2xl font-bold text-ink mb-6 text-center">The Abstraction That Makes This Possible</h3>
          <div className="bg-code rounded-lg p-6 overflow-x-auto">
            <pre className="text-sm text-paper/90 font-mono leading-relaxed"><code>{`// The entire scheduling abstraction — 40 lines
// Runtime never knows which policy runs

pub trait SchedulingPolicy {
    fn schedule(
        &self,
        modules: Vec<Module>,
        state: RobotState,
        context: RuntimeContext,
        events: Vec<Event>,
    ) -> ExecutionPlan;
}

// Swap policies at construction — zero runtime cost
let scheduler = Scheduler(LexicographicRiskAwareSchedulingPolicy::new());
// let scheduler = Scheduler(CriticalitySchedulingPolicy::new());
// let scheduler = Scheduler(RiskAwareKnapsackSchedulingPolicy::new());
// let scheduler = Scheduler(OperatorSchedulingPolicy::new());`}</code></pre>
          </div>
        </motion.div>
      </div>
    </section>
  );
}