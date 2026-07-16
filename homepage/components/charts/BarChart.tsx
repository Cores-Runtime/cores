"use client";

import { useRef, useEffect } from "react";
import { benchmarkData } from "@/lib/benchmark-data";

interface BarChartProps {
  id: string;
  data: typeof benchmarkData;
  metric: keyof typeof benchmarkData.policies[0];
  className?: string;
}

const POLICY_ORDER = ["priority", "criticality", "risk_aware_knapsack", "lexicographic"];
const POLICY_LABELS = ["Priority", "Criticality", "Knapsack", "Lexicographic"];
const POLICY_COLORS: Record<string, string> = {
  priority: "#6B7280",
  criticality: "#3B82F6",
  risk_aware_knapsack: "#8B5CF6",
  lexicographic: "#F59E0B",
};

function getMetricLabel(metric: string): string {
  if (metric === "missionUtility") return "Mission Utility (%)";
  if (metric === "safetyCoverage") return "Safety Coverage (%)";
  if (metric === "energyHeadroom") return "Energy Headroom (%)";
  return "Decision Time (ms)";
}

export function BarChart({ id, data, metric, className }: BarChartProps) {
  const containerRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = 1000;
    const height = 400;
    const margin = { top: 50, right: 24, bottom: 100, left: 80 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;

    const policies = POLICY_ORDER;
    const scenarios = data.scenarios;
    const numScenarios = scenarios.length;
    const numPolicies = policies.length;

    const groupWidth = plotWidth / Math.max(numScenarios, 1);
    const barGroupInner = groupWidth * 0.75;
    const barWidth = barGroupInner / Math.max(numPolicies, 1);

    let maxValue = 0;
    for (const policy of policies) {
      const policyData = data.policies.find(p => p.id === policy);
      if (policyData) {
        const values = policyData[metric] as number[];
        for (const v of values) {
          if (v > maxValue) maxValue = v;
        }
      }
    }
    if (maxValue === 0) maxValue = 1;

    const yScale = (val: number) => {
      if (maxValue === 0) return margin.top + plotHeight;
      return margin.top + plotHeight - (val / maxValue) * plotHeight;
    };

    const barHeight = (val: number) => {
      if (maxValue === 0) return 0;
      return (val / maxValue) * plotHeight;
    };

    const yLabel = (val: number) => (maxValue * val / 4).toFixed(metric === "decisionTimeMs" ? 2 : 1);

    const metricLabel = getMetricLabel(metric);

    let html = `
      <defs>
        ${POLICY_ORDER.map((policy, pi) => `
          <linearGradient id="bar-gradient-${id}-${policy}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${POLICY_COLORS[policies[pi]]}" stop-opacity="0.95"/>
            <stop offset="100%" stop-color="${POLICY_COLORS[policies[pi]]}" stop-opacity="0.4"/>
          </linearGradient>
        `).join("")}
      </defs>
      <rect width="100%" height="100%" fill="#FAFAF8"/>
      <text x="${width/2}" y="28" font-size="14" text-anchor="middle" fill="#111827" font-weight="600">
        ${getMetricLabel(metric)}
      </text>
    `;

    // Y-axis grid lines and labels
    for (let tick = 0; tick <= 4; tick++) {
      const y = margin.top + (plotHeight * tick) / 4;
      const val = yLabel(tick);
      html += `
        <line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="#E5E7EB" stroke-width="1"/>
        <text x="${margin.left - 10}" y="${y + 4}" font-size="11" text-anchor="end" fill="#6B7280" font-family="JetBrains Mono, monospace">${val}</text>
      `;
    }

    // Bars - use policy-specific colors
    for (let pi = 0; pi < POLICY_ORDER.length; pi++) {
      const policy = POLICY_ORDER[pi];
      const policyData = data.policies.find(p => p.id === policy);
      if (!policyData) continue;
      const values = policyData[metric] as number[];
      const policyColor = POLICY_COLORS[policy];

      for (let si = 0; si < numScenarios; si++) {
        const val = values[si] || 0;
        const x = margin.left + si * groupWidth + (groupWidth - barGroupInner) / 2 + pi * barWidth;
        const y = yScale(val);
        const h = barHeight(val);

        html += `
          <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(barWidth - 4).toFixed(1)}" height="${h.toFixed(1)}" 
                fill="url(#bar-gradient-${id}-${policy})" rx="2" opacity="${policy === "lexicographic" ? 1 : 0.9}"/>
        `;
      }
    }

    // X-axis labels
    for (let si = 0; si < numScenarios; si++) {
      const x = margin.left + si * groupWidth + groupWidth / 2;
      const name = scenarios[si];
      const lines = name.split(" ");
      html += `
        <text x="${x}" y="${height - 50}" font-size="9" text-anchor="middle" fill="#6B7280" 
              transform="rotate(-45, ${x}, ${height - 50})" font-weight="500">
          ${lines.join(" ")}
        </text>
      `;
    }

    // Legend - moved to bottom with background
    html += `
      <g class="legend">
        <rect x="${margin.left}" y="${height - 40}" width="${plotWidth}" height="35" fill="#FAFAF8" rx="4" stroke="#E5E7EB" stroke-width="1"/>
        ${POLICY_LABELS.map((label, i) => `
          <g transform="translate(${margin.left + i * (plotWidth / 4) + 20}, ${height - 28})">
            <rect x="0" y="0" width="12" height="12" fill="${POLICY_COLORS[POLICY_ORDER[i]]}" rx="2"/>
            <text x="18" y="9" font-size="11" fill="#111827" font-weight="500">${label}</text>
          </g>
        `).join("")}
      </g>
    `;

    const container = containerRef.current;
    if (container) container.innerHTML = html;
  }, [id, metric]);

  return (
    <svg ref={containerRef} id={`bar-chart-${id}`} className={className} viewBox="0 0 1000 400" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
      <rect width="100%" height="100%" fill="#FAFAF8" />
    </svg>
  );
}