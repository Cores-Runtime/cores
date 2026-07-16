"use client";

import Link from "next/link";

export function Footer() {
  return (
    <footer className="py-16 px-6 bg-ink text-paper/60">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-4 gap-8 mb-12">
          <div className="md:col-span-2">
            <h3 className="text-xl font-bold text-paper mb-4">CORES</h3>
            <p className="text-paper/40 max-w-md leading-relaxed">
              Cognitive Runtime for Embodied Systems. Deterministic. Modular. 
              Built for research that ships on real robots.
            </p>
          </div>
          <div>
            <h4 className="font-medium text-paper mb-4">Modules</h4>
            <ul className="space-y-2 text-sm text-paper/50 hover:text-paper/80 transition-colors">
              <li><Link href="#modules" className="link-underline">Runtime Foundation</Link></li>
              <li><Link href="#modules" className="link-underline">Criticality Scheduling</Link></li>
              <li><Link href="#modules" className="link-underline">Risk-Aware Knapsack</Link></li>
              <li><Link href="#modules" className="link-underline">Lexicographic Scheduler</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-paper mb-4">Artifacts</h4>
            <ul className="space-y-2 text-sm text-paper/50 hover:text-paper/80 transition-colors">
              <li><Link href="#" className="link-underline">Validation Reports (Markdown)</Link></li>
              <li><Link href="#" className="link-underline">Comparison Tables (CSV)</Link></li>
              <li><Link href="#" className="link-underline">Charts (SVG)</Link></li>
              <li><Link href="#" className="link-underline">Ablation Data (CSV)</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-paper/10 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-paper/40">
            CORES Runtime — deterministic, modular, dependency-free.
          </p>
          <div className="flex items-center gap-6 text-sm text-paper/40">
            <Link href="#" className="hover:text-paper transition-colors">GitHub</Link>
            <Link href="#" className="hover:text-paper transition-colors">Documentation</Link>
            <Link href="#" className="hover:text-paper transition-colors">API Reference</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}