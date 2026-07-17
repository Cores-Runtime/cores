"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSimulator } from "./RuntimeContext";

const statusStyles: Record<string, string> = {
  running: "bg-emerald-500",
  thinking: "bg-amber-500",
  sleeping: "bg-gray-400",
  suspended: "bg-red-500",
};

export function RuntimeModules() {
  const { engine } = useSimulator();
  const [selected, setSelected] = useState<string | null>(null);
  const entries = Object.entries(engine.modules);
  const defs = engine.activeMission?.modules || [];

  return (
    <div className="glass p-5">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-4">Runtime Modules</h3>
      <div className="grid grid-cols-3 gap-2">
        {entries.map(([id, mod]) => {
          const def = defs.find(m => m.id === id);
          return (
            <motion.button
              key={id}
              className={`relative text-left p-2.5 rounded-lg border transition-all duration-200 ${
                selected === id ? "border-accent bg-accent/5 shadow-sm" : "border-white/10 bg-white/40 hover:bg-white/60"
              }`}
              onClick={() => setSelected(selected === id ? null : id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span className={`w-1.5 h-1.5 rounded-full ${statusStyles[mod.status]}`} />
                <span className="text-xs font-bold text-ink">{def?.name || id}</span>
              </div>
              <div className={`text-[10px] font-medium ${
                mod.status === "running" ? "text-emerald-600" :
                mod.status === "thinking" ? "text-amber-600" :
                mod.status === "suspended" ? "text-red-500" : "text-gray-400"
              }`}>{mod.status.toUpperCase()}</div>
              <div className="text-[9px] text-muted/50 mt-0.5 leading-tight">{mod.reason}</div>
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
              className="mt-3 p-3 rounded-lg bg-white/50 border border-white/10 text-xs"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <div className="font-semibold text-ink mb-1">{def.name}</div>
              <div className="text-muted/70 mb-2">{def.purpose}</div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted/50">
                <span>CPU: {mod.cpu}%</span>
                <span>Task: {mod.task}</span>
                <span>Wake Count: {mod.wakeCount}</span>
                <span>Status: {mod.status}</span>
              </div>
              {def.deps.length > 0 && (
                <div className="mt-1 text-muted/50">
                  <span className="font-medium">Depends on: </span>{def.deps.join(", ")}
                </div>
              )}
            </motion.div>
          );
        })()}
      </AnimatePresence>
    </div>
  );
}
