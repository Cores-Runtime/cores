"use client";

import { motion } from "framer-motion";
import { useSimulator } from "./RuntimeContext";

export function ScenarioControls() {
  const { injectableEvents, injectEvent, loadMission, missions, mission, engine, running, setRunning } = useSimulator();

  return (
    <div className="glass p-5 col-span-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-bold text-ink uppercase tracking-wider">Scenario Controls</h3>
        <button
          className={`text-xs px-4 py-1.5 rounded-lg font-medium transition-all ${
            running
              ? "bg-red-500/10 text-red-600 border border-red-200/30 hover:bg-red-500/20"
              : "bg-emerald-500/10 text-emerald-600 border border-emerald-200/30 hover:bg-emerald-500/20"
          }`}
          onClick={() => setRunning(!running)}
        >
          {running ? "Stop" : "Run"}
        </button>
      </div>

      {!mission && (
        <div className="mb-4">
          <div className="text-[10px] text-muted/50 uppercase mb-2">Select Mission</div>
          <div className="flex flex-wrap gap-2">
            {missions.map((m) => (
              <motion.button
                key={m.id}
                className="px-3 py-2 rounded-lg text-xs font-medium bg-white/40 border border-white/10 text-ink/70 hover:bg-accent/10 hover:border-accent/30 hover:text-accent transition-all text-left"
                onClick={() => loadMission(m.id)}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                <div className="font-bold">{m.name}</div>
                <div className="text-[9px] text-muted/50 mt-0.5">{m.desc.slice(0, 60)}...</div>
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {mission && (
        <div>
          <div className="text-xs font-semibold text-ink mb-2">
            {mission.name}
            <span className="text-muted/50 font-normal text-[10px] ml-2">T{engine.tick}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {injectableEvents.map((ev) => (
              <motion.button
                key={ev.name}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/40 border border-white/10 text-ink/70 hover:bg-red-50 hover:border-red-200/50 hover:text-red-600 transition-all"
                onClick={() => injectEvent(ev.name)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {ev.name}
              </motion.button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
