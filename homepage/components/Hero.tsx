"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { metrics } from "@/lib/data";
import { BrainNodes } from "@/components/BrainNodes";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-accent/5 via-transparent to-transparent" />

      <BrainNodes />

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-20 text-center w-full">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 text-accent text-sm font-medium mb-8 border border-accent/20">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
            </span>
            Cognitive Scheduling for Autonomous Robots
          </span>

          <h1 className="font-bold tracking-tight text-ink mb-4 text-balance leading-[1.1]">
            <span className="text-6xl md:text-8xl lg:text-9xl block">CORES</span>
            <span className="text-xl md:text-2xl lg:text-3xl text-muted font-normal block mt-3 max-w-3xl mx-auto leading-relaxed">
              Linux schedules processes.
              <br />
              CORES schedules cognition.
            </span>
          </h1>

          <p className="text-base md:text-lg text-muted/70 max-w-2xl mx-auto mb-10 text-balance leading-relaxed">
            A deterministic, modular runtime for autonomous robotics.
            Lexicographic scheduling over safety, mission, and energy constraints.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10">
            <Link href="#modules" className="btn-primary text-base px-8 py-3">
              Explore Modules
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </Link>
            <Link href="#policies" className="btn-secondary text-base px-8 py-3">
              Compare Policies
            </Link>
          </div>

          <motion.div
            className="inline-flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.6 }}
          >
            <span className="flex items-center gap-2 text-muted/70">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Runtime Core
            </span>
            <span className="w-px h-4 bg-border" />
            <span className="flex items-center gap-2 text-muted/70">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              Criticality
            </span>
            <span className="w-px h-4 bg-border" />
            <span className="flex items-center gap-2 text-muted/70">
              <span className="w-2 h-2 rounded-full bg-violet-500" />
              Knapsack
            </span>
            <span className="w-px h-4 bg-border" />
            <span className="flex items-center gap-2 text-muted/70">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              Lexicographic
            </span>
          </motion.div>
        </motion.div>

        <motion.div
          className="mt-14"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        >
          <div className="inline-flex flex-wrap items-stretch gap-px divide-x divide-white/10 rounded-xl border border-white/20 overflow-hidden bg-white/60 backdrop-blur-xl shadow-xl shadow-black/5">
            <div className="px-5 py-3 flex items-center gap-2.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" style={{ animationDuration: "2s" }} />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <div className="text-left">
                <div className="text-xs text-muted/50">Status</div>
                <div className="text-sm font-semibold text-emerald-600">Runtime Online</div>
              </div>
            </div>
            <div className="px-5 py-3 flex items-center gap-2.5">
              <div className="text-left">
                <div className="text-xs text-muted/50">Battery</div>
                <div className="text-sm font-semibold text-ink">84%</div>
              </div>
            </div>
            <div className="px-5 py-3 flex items-center gap-2.5">
              <div className="text-left">
                <div className="text-xs text-muted/50">Mission</div>
                <div className="text-sm font-semibold text-ink">Explore</div>
              </div>
            </div>
            <div className="px-5 py-3 flex items-center gap-2.5">
              <div className="text-left">
                <div className="text-xs text-muted/50">Latency</div>
                <div className="text-sm font-semibold text-ink">&lt; 1 ms</div>
              </div>
            </div>
            <div className="px-5 py-3 flex items-center gap-2.5">
              <div className="text-left">
                <div className="text-xs text-muted/50">Events</div>
                <div className="text-sm font-semibold text-ink">128</div>
              </div>
            </div>
            <div className="px-5 py-3 flex items-center gap-2.5">
              <div className="text-left">
                <div className="text-xs text-muted/50">Modules</div>
                <div className="text-sm font-semibold text-ink">6 / 9 Active</div>
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div
          className="mt-14 grid md:grid-cols-2 gap-8 items-start max-w-5xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.5 }}
        >
          <div className="grid grid-cols-2 gap-3">
            {metrics.map((m, i) => (
              <motion.div
                key={m.label}
                className="glass p-5 text-left"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + i * 0.05, duration: 0.4 }}
              >
                <div className="text-3xl md:text-4xl font-bold text-ink mb-1">{m.value}</div>
                <div className="text-sm font-semibold text-muted">{m.label}</div>
                <div className="text-xs text-muted/50 mt-1 leading-relaxed">{m.detail}</div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="glass p-6 sticky top-24"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8, duration: 0.6 }}
          >
            <h3 className="text-sm font-semibold text-ink mb-5 text-center tracking-wide uppercase">Execution Cycle</h3>
            <svg viewBox="0 0 320 400" className="w-full" style={{ maxHeight: 360 }}>
              <defs>
                <marker id="flowArrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#F59E0B" />
                </marker>
              </defs>

              {[
                { x: 160, y: 20, w: 120, h: 44, label: "Collect Events", desc: "Flush buffer", color: "#3B82F6" },
                { x: 160, y: 96, w: 120, h: 44, label: "Schedule", desc: "Policy selects", color: "#F59E0B" },
                { x: 160, y: 172, w: 120, h: 44, label: "ExecutionPlan", desc: "Ordered modules", color: "#8B5CF6" },
                { x: 160, y: 248, w: 120, h: 44, label: "Execute", desc: "Invoke modules", color: "#DC2626" },
                { x: 160, y: 324, w: 120, h: 44, label: "Publish Events", desc: "Dispatch results", color: "#0D7A33" },
              ].map((box, i) => (
                <g key={box.label}>
                  <rect x={box.x - box.w / 2} y={box.y} width={box.w} height={box.h} rx="8" fill={`${box.color}15`} stroke={box.color} strokeWidth="1.5" />
                  <text x={box.x} y={box.y + 20} textAnchor="middle" fill={box.color} fontSize="12" fontWeight="700" fontFamily="Inter, sans-serif">{box.label}</text>
                  <text x={box.x} y={box.y + 36} textAnchor="middle" fill="#78716C" fontSize="10" fontFamily="Inter, sans-serif">{box.desc}</text>
                  {i < 4 && (
                    <line x1={box.x} y1={box.y + box.h} x2={box.x} y2={324 - (3 - i) * 76} stroke="#F59E0B" strokeWidth="1.5" markerEnd="url(#flowArrow)" strokeOpacity="0.5" />
                  )}
                </g>
              ))}

              <text x={160} y={388} textAnchor="middle" fill="#A8A29E" fontSize="9" fontFamily="Inter, sans-serif">One call to Runtime.step()</text>
            </svg>
          </motion.div>
        </motion.div>
      </div>

      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce">
        <svg className="w-6 h-6 text-muted/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </section>
  );
}
