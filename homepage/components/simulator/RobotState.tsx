"use client";

import { useSimulator } from "./RuntimeContext";

export function RobotState() {
  const { engine } = useSimulator();
  const w = engine.world;
  const r = engine.robot;

  return (
    <div className="glass p-5">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-4">Robot State</h3>
      <div className="space-y-3 text-sm">
        <div>
          <div className="text-[10px] text-muted/50 uppercase">Position</div>
          <div className="font-mono text-xs text-ink">({r.x.toFixed(1)}, {r.y.toFixed(1)})  {r.heading}°</div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {[
            ["Terrain", w.terrain],
            ["Slope", `${w.slope.toFixed(1)}°`],
            ["Obstacle", `${w.obstacleDistance.toFixed(1)} m`],
            ["Wheel Health", `${Math.round(w.wheelHealth)}%`],
          ].map(([l, v]) => (
            <div key={l}>
              <div className="text-[10px] text-muted/50 uppercase">{l}</div>
              <div className="text-xs font-semibold text-ink">{v}</div>
            </div>
          ))}
        </div>

        <div>
          <div className="text-[10px] text-muted/50 uppercase mb-1.5">Sensors</div>
          <div className="grid grid-cols-2 gap-1.5">
            {[
              ["gps", w.gpsQuality],
              ["camera", w.cameraQuality],
              ["lidar", w.lidarQuality],
              ["comms", w.commsQuality],
            ].map(([s, q]) => (
              <div key={s} className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${(q as number) > 0.5 ? "bg-emerald-500" : (q as number) > 0.1 ? "bg-amber-500" : "bg-red-500"}`} />
                <span className="text-[11px] capitalize text-ink/70">{s}</span>
                <span className="text-[11px] text-muted/50 ml-auto">{(q as number) > 0.5 ? "Online" : (q as number) > 0.1 ? "Degraded" : "Lost"}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-white/10">
          <span className="text-[10px] text-muted/50 uppercase">Power State</span>
          <span className={`text-xs font-semibold ${r.powerState === "Nominal" ? "text-emerald-600" : "text-amber-600"}`}>{r.powerState}</span>
        </div>
      </div>
    </div>
  );
}
