"use client";

import { motion } from "framer-motion";
import { useSimulator } from "./RuntimeContext";

export function ScenarioControls() {
  const { injectableEvents, injectEvent, loadMission, missions, mission, engine, running, setRunning, tick } = useSimulator();

  return (
    <div className="glass p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-bold text-ink uppercase tracking-wider">Controls</h3>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-muted/50">T{tick}</span>
          <button
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all ${
              running
                ? "bg-red-500/10 text-red-600 border border-red-200/30 hover:bg-red-500/20"
                : "bg-emerald-500/10 text-emerald-600 border border-emerald-200/30 hover:bg-emerald-500/20"
            }`}
            onClick={() => setRunning(!running)}
          >
            {running ? "Pause" : "Resume"}
          </button>
          <button
            className="text-xs px-3 py-1.5 rounded-lg font-medium bg-white/40 border border-white/10 text-ink/70 hover:bg-accent/10 hover:border-accent/30 hover:text-accent transition-all"
            onClick={() => missions.length > 0 && loadMission(missions[0].id)}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {injectableEvents.map((ev) => (
          <motion.button
            key={ev.name}
            className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-white/40 border border-white/10 text-ink/70 hover:bg-red-50 hover:border-red-200/50 hover:text-red-600 transition-all"
            onClick={() => injectEvent(ev.name)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {ev.name}
          </motion.button>
        ))}
      </div>
    </div>
  );
}
