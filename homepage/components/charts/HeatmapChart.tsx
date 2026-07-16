"use client";

import { useRef, useEffect } from "react";
import { heatmapData } from "@/lib/benchmark-data";

interface HeatmapChartProps {
  id: string;
  data: any;
  color: string;
  className?: string;
}

const POLICY_LABELS = ["Priority", "Criticality", "Knapsack", "Lexicographic"];
const POLICY_COLORS = ["#6B7280", "#3B82F6", "#8B5CF6", "#F59E0B"];

const COLOR_SCALES: Record<string, { min: string; max: string }> = {
  amber: { min: "#FEF3C7", max: "#B45309" },
  emerald: { min: "#D1FAE5", max: "#065F46" },
  blue: { min: "#DBEAFE", max: "#1E40AF" },
  violet: { min: "#F0F0FF", max: "#4C1D95" },
};

export function HeatmapChart({ id, data, color, className }: HeatmapChartProps) {
  const containerRef = useRef<SVGSVGElement>(null);
  const policyKeys = ["priority", "criticality", "risk_aware_knapsack", "lexicographic"];

  useEffect(() => {
    const containerEl = document.getElementById(`heatmap-${id}`);
    if (!containerEl) return;

    const metricKey = `${color === "amber" ? "missionUtility" : color === "emerald" ? "safetyCoverage" : color === "blue" ? "energyHeadroom" : "decisionTime"}` as keyof typeof heatmapData;
    const matrix = heatmapData[metricKey] as number[][];
    const scenarios = heatmapData.scenarios;
    const allVals = matrix.flat();
    const minVal = Math.min(...allVals);
    const maxVal = Math.max(...allVals);
    const scale = COLOR_SCALES[color] || COLOR_SCALES.amber;

    const width = 1000;
    const height = 600;
    const margin = { top: 80, right: 140, bottom: 100, left: 200 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const cellWidth = plotWidth / 4;
    const cellHeight = plotHeight / scenarios.length;

    const getColor = (val: number) => {
      const t = (val - minVal) / (maxVal - minVal);
      const p = Math.pow(t, 0.45);
      const r = Math.round(
        parseInt(scale.min.slice(1, 3), 16) * (1 - p) +
        parseInt(scale.max.slice(1, 3), 16) * p
      );
      const g = Math.round(
        parseInt(scale.min.slice(3, 5), 16) * (1 - p) +
        parseInt(scale.max.slice(3, 5), 16) * p
      );
      const b = Math.round(
        parseInt(scale.min.slice(5, 7), 16) * (1 - p) +
        parseInt(scale.max.slice(5, 7), 16) * p
      );
      return `rgb(${r}, ${g}, ${b})`;
    };

    let html = `
      <rect width="100%" height="100%" fill="#FAFAF8"/>
      <text x="500" y="25" text-anchor="middle" font-size="16" font-weight="600" fill="#111827">
        ${id.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
      </text>
    `;

    for (let i = 0; i < scenarios.length; i++) {
      const y = margin.top + i * cellHeight + cellHeight / 2;
      html += `
        <text x="${margin.left - 12}" y="${y + 4}" font-size="11" text-anchor="end" fill="#111827" font-weight="600">
          ${scenarios[i]}
        </text>
      `;
    }

    for (let j = 0; j < 4; j++) {
      html += `
        <text x="${margin.left + j * cellWidth + cellWidth / 2}" 
              y="${margin.top - 15}" 
              text-anchor="middle" font-size="11" fill="#111827" font-weight="600">
          ${POLICY_LABELS[j]}
        </text>
      `;
    }

    for (let i = 0; i < scenarios.length; i++) {
      for (let j = 0; j < 4; j++) {
        const val = matrix[j][i];
        const cellColor = getColor(val);
        const textColor = (val - minVal) / (maxVal - minVal) > 0.5 ? "#FFFFFF" : "#111827";
        html += `
          <rect x="${margin.left + j * cellWidth}" y="${margin.top + i * cellHeight}" 
                width="${cellWidth - 1}" height="${cellHeight - 1}" fill="${cellColor}" rx="2"/>
          <text x="${margin.left + j * cellWidth + cellWidth / 2}" 
                y="${margin.top + i * cellHeight + cellHeight / 2 + 4}" 
                font-size="10" text-anchor="middle" fill="${textColor}" font-weight="600">
            ${val.toFixed(2)}
          </text>
        `;
      }
    }

    html += `
      <g transform="translate(${width - 100}, ${margin.top})">
        <rect x="0" y="0" width="15" height="${plotHeight}" fill="url(#heatmap-gradient-${id})" rx="3"/>
        ${[0, 1, 2, 3, 4].map(t => {
          const val = minVal + (maxVal - minVal) * (4 - t) / 4;
          const y = (t / 4) * plotHeight;
          return `<text x="25" y="${y + 4}" font-size="10" fill="#374151">${val.toFixed(2)}</text>`;
        }).join("")}
      </g>
      <defs>
        <linearGradient id="heatmap-gradient-${id}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${scale.max}"/>
          <stop offset="100%" stop-color="${scale.min}"/>
        </linearGradient>
      </defs>
    `;

    html += `
      <g transform="translate(${margin.left}, ${height - 30})">
        ${POLICY_LABELS.map((label, i) => `
          <g transform="translate(${i * (plotWidth / 4) + 20}, 0)">
            <rect x="0" y="0" width="12" height="12" fill="${POLICY_COLORS[i]}" rx="2"/>
            <text x="18" y="9" font-size="11" fill="#111827" font-weight="500">${label}</text>
          </g>
        `).join("")}
      </g>
    `;

    containerEl.innerHTML = html;
  }, [id, data, color]);

  return (
    <svg ref={containerRef} id={`heatmap-${id}`} className={className} viewBox="0 0 1000 600" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
      <rect width="100%" height="100%" fill="#FAFAF8" />
    </svg>
  );
}
