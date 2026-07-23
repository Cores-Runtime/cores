"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export function Hero() {
  return (
    <section className="min-h-screen flex items-center pt-28 pb-20">
      <div className="max-w-page mx-auto px-6 w-full">
        <div className="grid md:grid-cols-2 gap-20 items-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <span className="font-display text-[13px] tracking-tight text-brass uppercase">
              CORES v0.1
            </span>

            <h1 className="font-display text-display leading-display tracking-display text-graphite mt-4">
              <span className="block">A robot has</span>
              <span className="block">one battery,</span>
              <span className="block">one CPU, and</span>
              <span className="block">one chance</span>
              <span className="block">to get home.</span>
            </h1>

            <p className="font-sans text-subheading leading-subheading text-steel mt-6 max-w-md">
              CORES decides which cognitive modules run, in what order, and under what constraints. Every cycle. Deterministically.
            </p>

            <p className="font-sans text-caption leading-caption text-slate mt-3 max-w-sm">
              It is not the robot's brain. It is the infrastructure that keeps the brain from burning out.
            </p>

            <div className="flex items-center gap-4 mt-10">
              <Link href="#modules" className="btn-primary">
                Explore Modules
              </Link>
              <Link href="/simulator" className="btn-ghost">
                Open Simulator
              </Link>
            </div>

            <Link href="#modules" className="inline-block mt-8 font-sans text-[14px] text-graphite border-b border-ember-orange pb-0.5">
              Read the architecture decisions
            </Link>
          </motion.div>

          <motion.div
            className="relative"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <div className="card-data relative z-10">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-display text-[16px] tracking-tight text-graphite">Runtime Status</h3>
                <span className="font-display text-[13px] tracking-tight text-brass">Live</span>
              </div>
              <div className="grid grid-cols-2 gap-8">
                <div>
                  <div className="font-display text-[40px] leading-[1.2] tracking-tight text-graphite">84%</div>
                  <div className="font-sans text-[13px] text-slate mt-1">Battery</div>
                </div>
                <div>
                  <div className="font-display text-[40px] leading-[1.2] tracking-tight text-graphite">5</div>
                  <div className="font-sans text-[13px] text-slate mt-1">Modules Active</div>
                </div>
                <div>
                  <div className="font-display text-[40px] leading-[1.2] tracking-tight text-graphite">&lt;1ms</div>
                  <div className="font-sans text-[13px] text-slate mt-1">Latency</div>
                </div>
                <div>
                  <div className="font-display text-[40px] leading-[1.2] tracking-tight text-graphite">128</div>
                  <div className="font-sans text-[13px] text-slate mt-1">Events</div>
                </div>
              </div>
            </div>

            <div className="card-data relative z-20 -mt-4 ml-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-display text-[16px] tracking-tight text-graphite">Mission Utility</h3>
                <span className="font-sans text-[13px] text-slate">Lexicographic</span>
              </div>
              <svg viewBox="0 0 300 80" className="w-full">
                <defs>
                  <linearGradient id="lineFill" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#ff682c" stopOpacity="0.15" />
                    <stop offset="100%" stopColor="#ff682c" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <polyline
                  fill="none"
                  stroke="#ff682c"
                  strokeWidth="1.5"
                  points="0,65 30,55 60,60 90,40 120,35 150,20 180,25 210,10 240,15 270,5 300,8"
                />
                <polygon
                  fill="url(#lineFill)"
                  points="0,65 30,55 60,60 90,40 120,35 150,20 180,25 210,10 240,15 270,5 300,8 300,80 0,80"
                />
              </svg>
              <div className="flex justify-between mt-2">
                <span className="font-sans text-[12px] text-slate">Cycle 0</span>
                <span className="font-sans text-[12px] text-slate">Cycle 80</span>
              </div>
            </div>

            <div className="flex gap-4 relative z-30 -mt-4 ml-16">
              <div className="card-data flex-1">
                <div className="font-sans text-[13px] text-slate mb-3">Safety</div>
                <svg viewBox="0 0 120 120" className="w-20 h-20 mx-auto">
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#e8e8e8" strokeWidth="4" />
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#ff682c" strokeWidth="4"
                    strokeDasharray={`${2 * Math.PI * 50}`}
                    strokeDashoffset={`${2 * Math.PI * 50 * 0}`}
                    transform="rotate(-90 60 60)" />
                  <text x="60" y="56" textAnchor="middle" className="font-display text-[28px] tracking-tight" fill="#202020">100</text>
                  <text x="60" y="74" textAnchor="middle" className="font-sans text-[10px]" fill="#828282">%</text>
                </svg>
              </div>
              <div className="card-data flex-1">
                <div className="font-sans text-[13px] text-slate mb-3">Energy</div>
                <svg viewBox="0 0 120 120" className="w-20 h-20 mx-auto">
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#e8e8e8" strokeWidth="4" />
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#816729" strokeWidth="4"
                    strokeDasharray={`${2 * Math.PI * 50}`}
                    strokeDashoffset={`${2 * Math.PI * 50 * 0.4}`}
                    transform="rotate(-90 60 60)" />
                  <text x="60" y="56" textAnchor="middle" className="font-display text-[28px] tracking-tight" fill="#202020">60</text>
                  <text x="60" y="74" textAnchor="middle" className="font-sans text-[10px]" fill="#828282">%</text>
                </svg>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
