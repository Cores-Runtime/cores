"use client";

import { motion } from "framer-motion";
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
      <nav className="fixed top-0 left-0 right-0 z-50 bg-paper/80 backdrop-blur-md border-b border-border transition-all duration-200">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-ink text-lg">
            <span className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-paper font-mono text-sm">CR</span>
            CORES
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link href="#modules" className="text-sm text-muted hover:text-ink transition-colors">Modules</Link>
            <Link href="#policies" className="text-sm text-muted hover:text-ink transition-colors">Policies</Link>
            <Link href="#scenarios" className="text-sm text-muted hover:text-ink transition-colors">Scenarios</Link>
            <Link href="#visualizations" className="text-sm text-muted hover:text-ink transition-colors">Visualizations</Link>
            <Link href="/simulator" className="text-sm text-accent font-medium hover:text-accentHover transition-colors">Simulator</Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="#policies" className="btn-secondary text-sm px-4 py-2">Compare Policies</Link>
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