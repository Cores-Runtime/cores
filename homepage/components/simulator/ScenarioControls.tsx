"use client";

import { useSimulator } from "./RuntimeContext";

export function ScenarioControls() {
  const { injectableEvents, injectEvent, loadMission, missions, running, setRunning, tick, mode, setMode, wsUrl, setWsUrl } = useSimulator();

  return (
    <div>
      <h3 className="font-display text-[12px] tracking-tight text-slate uppercase mb-3">Controls</h3>
      <div className="bg-ash rounded-[6px_0px_0px] px-6 py-4">
        <div className="flex items-center flex-wrap gap-3">
          <div className="flex items-center gap-[1px]">
            <button
              className={`font-sans text-[12px] px-3 py-1.5 transition-all ${
                mode === "replay"
                  ? "bg-graphite text-canvas-white"
                  : "bg-canvas-white text-slate hover:text-graphite"
              }`}
              onClick={() => setMode("replay")}
            >
              Replay
            </button>
            <button
              className={`font-sans text-[12px] px-3 py-1.5 transition-all ${
                mode === "live"
                  ? "bg-graphite text-canvas-white"
                  : "bg-canvas-white text-slate hover:text-graphite"
              }`}
              onClick={() => setMode("live")}
            >
              Live
            </button>
          </div>

          <span className="font-mono text-[11px] text-slate tabular-nums">T{tick}</span>

          <button
            className={`font-sans text-[12px] px-4 py-1.5 border transition-all ${
              running
                ? "border-ember-orange text-ember-orange bg-ember-orange/5 hover:bg-ember-orange/10"
                : "border-graphite text-graphite hover:bg-graphite/5"
            }`}
            onClick={() => setRunning(!running)}
          >
            {running ? "Pause" : "Run"}
          </button>

          {mode === "replay" && (
            <button
              className="font-sans text-[12px] px-4 py-1.5 border border-mist text-slate hover:text-graphite hover:border-graphite transition-all"
              onClick={() => missions.length > 0 && loadMission(missions[0].id)}
            >
              Reset
            </button>
          )}

          <div className="flex items-center flex-wrap gap-1.5 ml-auto">
            {injectableEvents.map((ev) => (
              <button
                key={ev.name}
                className="font-sans text-[11px] px-2.5 py-1 border border-mist text-slate hover:text-ember-orange hover:border-ember-orange transition-all"
                onClick={() => injectEvent(ev.name)}
              >
                {ev.name}
              </button>
            ))}
          </div>
        </div>

        {mode === "live" && (
          <div className="mt-3 pt-3 border-t border-mist">
            <input
              type="text"
              value={wsUrl}
              onChange={(e) => setWsUrl(e.target.value)}
              placeholder="ws://127.0.0.1:8765"
              className="w-full px-3 py-1.5 font-mono text-[12px] bg-canvas-white text-graphite rounded-none focus:outline-none focus:ring-1 focus:ring-graphite"
            />
          </div>
        )}
      </div>
    </div>
  );
}
