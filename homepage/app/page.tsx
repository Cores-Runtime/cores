"use client";

import Link from "next/link";
import { Hero } from "@/components/Hero";
import { ModulesSection } from "@/components/ModulesSection";
import { Policies } from "@/components/Policies";
import { ScenarioList } from "@/components/ScenarioList";
import { Visualizations } from "@/components/Visualizations";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 bg-canvas-white/80 backdrop-blur-md">
        <div className="max-w-page mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="font-display text-base tracking-tight text-graphite">
            CORES
          </Link>

          <div className="nav-pill flex items-center gap-5">
            <Link href="#modules" className="font-display text-base tracking-tight text-graphite hover:text-steel transition-colors flex items-center gap-1">
              Modules
              <svg className="w-3 h-3 text-slate" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" /></svg>
            </Link>
            <Link href="#policies" className="font-display text-base tracking-tight text-graphite hover:text-steel transition-colors flex items-center gap-1">
              Policies
              <svg className="w-3 h-3 text-slate" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" /></svg>
            </Link>
            <Link href="#scenarios" className="font-display text-base tracking-tight text-graphite hover:text-steel transition-colors flex items-center gap-1">
              Scenarios
              <svg className="w-3 h-3 text-slate" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" /></svg>
            </Link>
            <Link href="#visualizations" className="font-display text-base tracking-tight text-graphite hover:text-steel transition-colors flex items-center gap-1">
              Data
              <svg className="w-3 h-3 text-slate" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" /></svg>
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <Link href="/simulator" className="btn-primary text-sm px-4 py-2">
              Simulator
            </Link>
          </div>
        </div>
      </nav>

      <main>
        <Hero />
        <ModulesSection />
        <Policies />
        <ScenarioList />
        <Visualizations />
      </main>

      <Footer />
    </>
  );
}
