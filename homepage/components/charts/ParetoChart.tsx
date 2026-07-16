"use client";

import { useRef, useEffect } from "react";
import { paretoData } from "@/lib/benchmark-data";

interface ParetoChartProps {
  className?: string;
}

export function ParetoChart({ className }: ParetoChartProps) {
  const containerRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = containerRef.current;
    if (!svg) return;

    const width = 600;
    const height = 600;
    const margin = { top: 50, right: 60, bottom: 80, left: 80 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;

    const xMin = 0.75;
    const xMax = 1.05;
    const yMin = 0.0;
    const yMax = 0.65;

    const xScale = (v: number) => margin.left + ((v - xMin) / (xMax - xMin)) * plotWidth;
    const yScale = (v: number) => margin.top + plotHeight - ((v - yMin) / (yMax - yMin)) * plotHeight;

    const sorted = [...paretoData].sort((a, b) => a.safety - b.safety);
    let maxMission = -1;
    const frontier = sorted.filter(d => {
      if (d.mission > maxMission) {
        maxMission = d.mission;
        return true;
      }
      return false;
    }).sort((a, b) => a.safety - b.safety);

    const policyColors: Record<string, string> = {
      Priority: "#6B7280",
      Criticality: "#3B82F6",
      Knapsack: "#8B5CF6",
      Lexicographic: "#F59E0B",
      "No Lexicographic": "#EF4444",
      "No Mandatory": "#10B981",
      "No Safety-Critical": "#F97316",
      "No Module Classes": "#06B6D4",
    };

    let html = `<rect width="100%" height="100%" fill="#FAFAF8"/>`;

    // Grid
    for (let i = 0; i <= 5; i++) {
      const x = margin.left + (i / 5) * plotWidth;
      html += `<line x1="${x}" y1="${margin.top}" x2="${x}" y2="${margin.top + plotHeight}" stroke="#E5E7EB" stroke-width="1"/>`;
      const xVal = xMin + (i / 5) * (xMax - xMin);
      html += `<text x="${x}" y="${margin.top + plotHeight + 20}" text-anchor="middle" font-size="11" fill="#6B7280">${xVal.toFixed(2)}</text>`;
    }
    for (let i = 0; i <= 5; i++) {
      const y = margin.top + (i / 5) * plotHeight;
      html += `<line x1="${margin.left}" y1="${y}" x2="${margin.left + plotWidth}" y2="${y}" stroke="#E5E7EB" stroke-width="1"/>`;
      const yVal = yMax - (i / 5) * (yMax - yMin);
      html += `<text x="${margin.left - 10}" y="${y + 4}" text-anchor="end" font-size="11" fill="#6B7280">${yVal.toFixed(2)}</text>`;
    }

    // Axes
    html += `
      <line x1="${margin.left}" y1="${margin.top + plotHeight}" x2="${margin.left + plotWidth}" y2="${margin.top + plotHeight}" stroke="#374151" stroke-width="2"/>
      <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + plotHeight}" stroke="#374151" stroke-width="2"/>
      <text x="${margin.left + plotWidth / 2}" y="${height - 10}" text-anchor="middle" font-size="14" fill="#374151">Safety Coverage</text>
      <text x="15" y="${margin.top + plotHeight / 2}" text-anchor="middle" transform="rotate(-90, 15, ${margin.top + plotHeight / 2})" font-size="14" fill="#374151">Mission Utility</text>
    `;

    // Frontier line
    if (frontier.length >= 2) {
      const pathD = frontier.map(d => `${xScale(d.safety)},${yScale(d.mission)}`).join(" ");
      html += `<polyline points="${pathD}" fill="none" stroke="#F59E0B" stroke-width="3" stroke-dasharray="8,4"/>`;
    }

    // Points from actual paretoData
    for (const d of paretoData) {
      const cx = xScale(d.safety);
      const cy = yScale(d.mission);
      const color = policyColors[d.policy] || "#6B7280";
      html += `
        <circle cx="${cx}" cy="${cy}" r="7" fill="${color}" stroke="white" stroke-width="2"/>
        <text x="${cx + 10}" y="${cy - 6}" font-size="10" fill="#111827" font-weight="600">${d.policy}</text>
      `;
    }

    svg.innerHTML = html;
  }, []);

  return (
    <svg ref={containerRef} id="pareto-chart" className={className} viewBox="0 0 600 600" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
      <rect width="100%" height="100%" fill="#FAFAF8" />
    </svg>
  );
}
