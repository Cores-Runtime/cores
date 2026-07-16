"use client";

import { useRef, useEffect } from "react";
import { radarData } from "@/lib/benchmark-data";

interface RadarChartProps {
  id: string;
  data: typeof radarData;
  color: string;
  className?: string;
}

export function RadarChart({ id, data, color, className }: RadarChartProps) {
  const containerRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const container = document.getElementById(`radar-${id}`);
    if (!container) return;

    const width = 350;
    const height = 350;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 45;
    const numAxes = data.metrics.length;
    const angleStep = (2 * Math.PI) / numAxes;

    const getPoint = (axisIndex: number, level: number) => {
      const angle = axisIndex * (2 * Math.PI / numAxes) - Math.PI / 2;
      const r = (level / 5) * radius;
      return {
        x: centerX + r * Math.cos(angle),
        y: centerY + r * Math.sin(angle),
      };
    };

    const policies = data.policies;
    const metrics = data.metrics;
    const values = data.data;
    const colors = ["#6B7280", "#3B82F6", "#8B5CF6", "#F59E0B"];

    let html = `
      <defs>
        <linearGradient id="radar-grid-fade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#E5E7EB" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="#E5E7EB" stop-opacity="0"/>
        </linearGradient>
      </defs>
    `;

    // Grid rings
    for (let ring = 1; ring <= 5; ring++) {
      const r = radius * ring / 5;
      const points = [];
      for (let i = 0; i < numAxes; i++) {
        const angle = i * (2 * Math.PI / numAxes) - Math.PI / 2;
        const x = centerX + r * Math.cos(angle);
        const y = centerY + r * Math.sin(angle);
        points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
      }
      html += `<polygon points="${points.join(" ")}" fill="none" stroke="#E5E7EB" stroke-width="1" />`;
      // Ring label
      html += `<text x="${centerX}" y="${centerY - r - 5}" font-size="9" text-anchor="middle" fill="#6B7280">${(ring * 20)}%</text>`;
    }

    // Axes
    for (let i = 0; i < numAxes; i++) {
      const angle = i * (2 * Math.PI / numAxes) - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      html += `<line x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}" stroke="#E5E7EB" stroke-width="1" />`;

      const labelX = centerX + (radius + 18) * Math.cos(angle);
      const labelY = centerY + (radius + 18) * Math.sin(angle);
      const anchor = x < centerX ? "end" : x === centerX ? "middle" : "start";
      const dy = y === centerY ? "4" : y < centerY ? "-4" : "18";
      html += `<text x="${labelX}" y="${labelY}" text-anchor="${anchor}" dy="${dy}" font-size="10" fill="#374151" font-weight="500">${metrics[i]}</text>`;
    }

    // Policy polygons
    let pointHtml = "";
    for (let pi = 0; pi < policies.length; pi++) {
      const vals = data.data[pi];
      const points = [];
      for (let i = 0; i < numAxes; i++) {
        const angle = i * (2 * Math.PI / numAxes) - Math.PI / 2;
        const r = radius * Math.min(vals[i], 1);
        const x = centerX + r * Math.cos(angle);
        const y = centerY + r * Math.sin(angle);
        points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
      }
      const polygonColor = colors[pi];
      const policyName = policies[pi];
      const isLex = pi === 3;

      let polygonHtml = `
        <polygon points="${points.join(" ")}" fill="${polygonColor}33" stroke="${polygonColor}" stroke-width="${isLex ? "2.5" : "2"}" />
      `;

      // Points
      let pointHtml = "";
      for (let i = 0; i < numAxes; i++) {
        const angle = i * (2 * Math.PI / numAxes) - Math.PI / 2;
        const r = radius * Math.min(data.data[pi][i], 1);
        const x = centerX + r * Math.cos(angle);
        const y = centerY + r * Math.sin(angle);
        pointHtml += `<circle cx="${x}" cy="${y}" r="3" fill="${polygonColor}" stroke="white" stroke-width="2" />`;
      }

      // Add polygon and points to html
      html += `
        <polygon points="${points.join(" ")}" fill="${polygonColor}33" stroke="${polygonColor}" stroke-width="${isLex ? "2.5" : "2"}" />
        ${pointHtml}
      `;
    }

    // Legend
    let legendHtml = `<g class="legend" transform="translate(10, 10)">`;
    ["Priority", "Criticality", "Knapsack", "Lexicographic"].forEach((name, i) => {
      const c = colors[i];
      html += `
        <g transform="translate(0, ${i * 20})">
          <rect x="0" y="0" width="12" height="12" fill="${c}33" stroke="${c}" stroke-width="2" rx="2"/>
          <text x="18" y="11" font-size="11" fill="#374151">${["Priority", "Criticality", "Knapsack", "Lexicographic"][i]}</text>
        </g>
      `;
    });
    // Close the legend group
    // We'll add it to the html string
    html += `</g>`;

    const containerEl = document.getElementById(`radar-${id}`);
    if (containerEl) containerEl.innerHTML = html;
  }, [id, color]);

  return (
    <svg id={`radar-${id}`} className={className} viewBox="0 0 350 350" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
      <rect width="100%" height="100%" fill="#FAFAF8" />
    </svg>
  );
}