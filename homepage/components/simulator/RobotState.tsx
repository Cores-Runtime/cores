"use client";

import { useSimulator } from "./RuntimeContext";

export function RobotState() {
  const { engine } = useSimulator();
  const w = engine.world;
  const r = engine.robot;

  const sensors = [
    { label: "GPS", value: w.gpsQuality },
    { label: "Camera", value: w.cameraQuality },
    { label: "LIDAR", value: w.lidarQuality },
    { label: "Comms", value: w.commsQuality },
  ];

  return (
    <div>
      <h3 className="font-display text-[12px] tracking-tight text-slate uppercase mb-3">Robot</h3>
      <div className="bg-ash rounded-[6px_0px_0px] px-6 py-5 space-y-4">
        <div className="flex items-center justify-between">
          <span className="font-sans text-[11px] text-slate uppercase tracking-wider">Position</span>
          <span className="font-mono text-[12px] text-graphite tabular-nums">
            ({r.x.toFixed(1)}, {r.y.toFixed(1)}) {r.heading}°
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            ["Terrain", w.terrain],
            ["Slope", `${w.slope.toFixed(1)}°`],
            ["Obstacle", `${w.obstacleDistance.toFixed(1)}m`],
            ["Wheels", `${Math.round(w.wheelHealth)}%`],
          ].map(([l, v]) => (
            <div key={l}>
              <span className="font-sans text-[10px] text-slate uppercase tracking-wider block">{l}</span>
              <span className="font-mono text-[12px] text-graphite mt-0.5 block">{v}</span>
            </div>
          ))}
        </div>

        <div className="pt-3 border-t border-mist">
          <span className="font-sans text-[10px] text-slate uppercase tracking-wider block mb-2">Sensors</span>
          <div className="grid grid-cols-2 gap-2">
            {sensors.map((s) => (
              <div key={s.label} className="flex items-center gap-2">
                <span className={`w-[5px] h-[5px] rounded-full shrink-0 ${
                  s.value > 0.5 ? "bg-graphite" : s.value > 0.1 ? "bg-brass" : "bg-mist"
                }`} />
                <span className="font-sans text-[12px] text-graphite">{s.label}</span>
                <span className="font-sans text-[11px] text-slate ml-auto">
                  {s.value > 0.5 ? "Online" : s.value > 0.1 ? "Degraded" : "Lost"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-mist">
          <span className="font-sans text-[10px] text-slate uppercase tracking-wider">Power</span>
          <span className={`font-mono text-[12px] ${r.powerState === "Nominal" ? "text-graphite" : "text-ember-orange"}`}>
            {r.powerState}
          </span>
        </div>
      </div>
    </div>
  );
}
