"use client";

import { useEffect, useRef } from "react";

const nodes = [
  { id: "scheduler", label: "Scheduler", x: 250, y: 180 },
  { id: "planner", label: "Planner", x: 550, y: 180 },
  { id: "builder", label: "Builder", x: 400, y: 320 },
  { id: "traveller", label: "Traveller", x: 250, y: 460 },
  { id: "scientist", label: "Scientist", x: 550, y: 460 },
];

const connections = [
  ["scheduler", "planner"],
  ["scheduler", "builder"],
  ["planner", "builder"],
  ["builder", "traveller"],
  ["builder", "scientist"],
  ["traveller", "scientist"],
  ["scheduler", "traveller"],
  ["planner", "scientist"],
];

export function BrainNodes() {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const paths = document.querySelectorAll(".brain-path");
    paths.forEach((path, i) => {
      (path as SVGPathElement).style.animationDelay = `${i * 0.3}s`;
    });
  }, []);

  return (
    <svg ref={svgRef} className="absolute inset-0 w-full h-full" viewBox="0 0 800 640" preserveAspectRatio="xMidYMid meet" style={{ opacity: 0.5 }}>
      <defs>
        {nodes.map(n => (
          <radialGradient key={n.id} id={`glow-${n.id}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.6" />
            <stop offset="60%" stopColor="#F59E0B" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
          </radialGradient>
        ))}
      </defs>

      {connections.map(([a, b]) => {
        const from = nodes.find(n => n.id === a)!;
        const to = nodes.find(n => n.id === b)!;
        const midX = (from.x + to.x) / 2;
        const midY = (from.y + to.y) / 2;
        return (
          <g key={`${a}-${b}`}>
            <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#F59E0B" strokeOpacity="0.08" strokeWidth="1" />
            <line
              x1={from.x} y1={from.y} x2={to.x} y2={to.y}
              stroke="#F59E0B" strokeOpacity="0.25" strokeWidth="1.5"
              strokeDasharray="6 12"
              className="brain-path"
              style={{ animation: `dashFlow 3s linear infinite` }}
            />
          </g>
        );
      })}

      {nodes.map(n => (
        <g key={n.id}>
          <circle cx={n.x} cy={n.y} r="40" fill={`url(#glow-${n.id})`} className="animate-pulse" style={{ animationDuration: "3s" }} />
          <circle cx={n.x} cy={n.y} r="18" fill="#1C1917" stroke="#F59E0B" strokeWidth="1" strokeOpacity="0.6" />
          <circle cx={n.x} cy={n.y} r="4" fill="#F59E0B" opacity="0.8" />
          <text x={n.x} y={n.y + 34} textAnchor="middle" fill="#A8A29E" fontSize="11" fontWeight="500" fontFamily="var(--font-sans, Inter, sans-serif)">
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
