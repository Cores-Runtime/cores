"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSimulator } from "./RuntimeContext";

const statusDots: Record<string, string> = {
  running: "bg-ember-orange",
  thinking: "bg-brass",
  sleeping: "bg-mist",
  suspended: "bg-slate",
};

export function RuntimeModules() {
  const { engine } = useSimulator();
  const [selected, setSelected] = useState<string | null>(null);
  const entries = Object.entries(engine.modules);
  const defs = engine.activeMission?.modules || [];

  return (
    <div className="mb-5">
      <h3 className="font-display text-[12px] tracking-tight text-slate uppercase mb-3">Modules</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {entries.map(([id, mod]) => {
          const def = defs.find(m => m.id === id);
          const isSelected = selected === id;
          return (
            <motion.button
              key={id}
              className={`text-left px-4 py-3 transition-all ${
                isSelected
                  ? "bg-graphite rounded-[6px_0px_0px]"
                  : "bg-ash rounded-[6px_0px_0px] hover:bg-fog"
              }`}
              onClick={() => setSelected(isSelected ? null : id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`w-[5px] h-[5px] rounded-full shrink-0 ${statusDots[mod.status] || "bg-mist"}`} />
                <span className={`font-sans text-[12px] ${isSelected ? "text-canvas-white" : "text-graphite"}`}>
                  {def?.name || id}
                </span>
              </div>
              <span className={`font-sans text-[10px] block ${
                isSelected ? "text-canvas-white/60" : "text-slate"
              }`}>
                {mod.status.toUpperCase()}
              </span>
            </motion.button>
          );
        })}
      </div>

      <AnimatePresence>
        {selected && (() => {
          const mod = engine.modules[selected];
          const def = defs.find(m => m.id === selected);
          if (!mod || !def) return null;
          return (
            <motion.div
              key={selected}
              className="mt-3 bg-ash rounded-[6px_0px_0px] px-6 py-4"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <div className="font-display text-[14px] tracking-tight text-graphite mb-1">{def.name}</div>
              <div className="font-sans text-[12px] text-steel mb-3">{def.purpose}</div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                <span className="font-sans text-[11px] text-slate">CPU: {mod.cpu}%</span>
                <span className="font-sans text-[11px] text-slate">Task: {mod.task}</span>
                <span className="font-sans text-[11px] text-slate">Wake Count: {mod.wakeCount}</span>
                <span className="font-sans text-[11px] text-slate">Status: {mod.status}</span>
              </div>
              {def.deps.length > 0 && (
                <div className="mt-2 font-sans text-[11px] text-slate">
                  <span className="text-slate">Depends on: </span>{def.deps.join(", ")}
                </div>
              )}
            </motion.div>
          );
        })()}
      </AnimatePresence>
    </div>
  );
}
