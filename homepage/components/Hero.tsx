"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { metrics } from "@/lib/data";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-accent/5 via-transparent to-transparent" />
      <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5" />
      
      <div className="relative z-10 max-w-6xl mx-auto px-6 py-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 text-accent text-sm font-medium mb-8 border border-accent/20">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
            </span>
            Deterministic Scheduling for Autonomous Robots
          </span>

          <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight text-ink mb-6 text-balance">
            CORES
            <br />
            <span className="text-muted font-normal">Cognitive Runtime for Embodied Systems</span>
          </h1>

          <p className="text-lg md:text-xl text-muted max-w-3xl mx-auto mb-12 text-balance leading-relaxed">
            A deterministic, modular runtime for autonomous robotics.
            Lexicographic scheduling over safety, mission, and energy constraints.
            Research-grade. Real robots. No compromises.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
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

          <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-muted/70">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Runtime Core
            </span>
            <span className="w-px h-6 bg-border" />
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              Criticality Scheduling
            </span>
            <span className="w-px h-6 bg-border" />
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-violet-500" />
              Risk-Aware Knapsack
            </span>
            <span className="w-px h-6 bg-border" />
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              Lexicographic Optimization
            </span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.2 }}
        >
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-4xl mx-auto">
            {metrics.map((m, i) => (
              <motion.div
                key={m.label}
                className="card p-4 md:p-6 text-left"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.05 }}
              >
                <div className="text-3xl md:text-4xl font-bold text-ink mb-1">{m.value}</div>
                <div className="text-sm font-medium text-muted">{m.label}</div>
                <div className="text-xs text-muted/60 mt-1">{m.detail}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce">
        <svg className="w-6 h-6 text-muted/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </section>
  );
}