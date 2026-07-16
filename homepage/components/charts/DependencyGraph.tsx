"use client";

import { useRef, useEffect } from "react";
import { graphNodes, graphEdges } from "@/lib/benchmark-data";

interface DependencyGraphProps {
  className?: string;
}

const nodeColors: Record<string, string> = {
  mandatory: "#0D7A33",
  safety: "#DC2626",
  mission: "#F59E0B",
};

const edgeStyles: Record<string, { stroke: string; dash: string; label: string }> = {
  depends: { stroke: "#3B82F6", dash: "", label: "Depends On" },
  redundant: { stroke: "#8B5CF6", dash: "5,5", label: "Redundant With" },
  mutex: { stroke: "#DC2626", dash: "8,4", label: "Mutually Exclusive" },
  shared: { stroke: "#F59E0B", dash: "3,3", label: "Shares Info" },
};

export function DependencyGraph({ className }: DependencyGraphProps) {
  const containerRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = containerRef.current;
    if (!svg) return;

    let html = `<rect width="100%" height="100%" fill="#FAFAF8"/>`;

    html += `<defs>`;
    for (const [key, style] of Object.entries(edgeStyles)) {
      html += `
        <marker id="arrowhead-${key}" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 10 3.5, 0 7" fill="${style.stroke}"/>
        </marker>`;
    }
    html += `</defs>`;

    for (const edge of graphEdges) {
      const source = graphNodes.find(n => n.id === edge.source);
      const target = graphNodes.find(n => n.id === edge.target);
      if (!source || !target) continue;

      const style = edgeStyles[edge.type] || edgeStyles.depends;
      const midX = (source.x + target.x) / 2;
      const midY = (source.y + target.y) / 2;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const perpX = (-dy / dist) * 50;
      const perpY = (dx / dist) * 50;
      const ctrlX = midX + perpX;
      const ctrlY = midY + perpY;
      const dashAttr = style.dash ? `stroke-dasharray="${style.dash}"` : "";

      html += `
        <path d="M ${source.x} ${source.y} Q ${ctrlX} ${ctrlY} ${target.x} ${target.y}"
              fill="none" stroke="${style.stroke}" stroke-width="2" ${dashAttr}
              marker-end="url(#arrowhead-${edge.type})"/>`;
    }

    for (const node of graphNodes) {
      const color = nodeColors[node.type] || "#6B7280";
      const lines = node.label.split("\n");

      html += `
        <g transform="translate(${node.x}, ${node.y})">
          <ellipse cx="0" cy="0" rx="68" ry="26" fill="${color}" opacity="0.9" stroke="white" stroke-width="2"/>
          <text x="0" y="-4" text-anchor="middle" font-size="10" fill="white" font-weight="600">
            ${lines.map((line, i) => `<tspan x="0" dy="${i === 0 ? 0 : 12}">${line}</tspan>`).join("")}
          </text>
        </g>`;
    }

    html += `
      <g transform="translate(20, 490)">
        <text x="0" y="0" font-size="13" font-weight="700" fill="#111827">Node Types</text>
        <g transform="translate(0, 20)">
          <rect x="0" y="-4" width="14" height="14" rx="3" fill="#0D7A33"/>
          <text x="20" y="7" font-size="11" fill="#374151">Mandatory (Battery, Logger)</text>
        </g>
        <g transform="translate(0, 40)">
          <rect x="0" y="-4" width="14" height="14" rx="3" fill="#DC2626"/>
          <text x="20" y="7" font-size="11" fill="#374151">Safety-Critical</text>
        </g>
        <g transform="translate(0, 60)">
          <rect x="0" y="-4" width="14" height="14" rx="3" fill="#F59E0B"/>
          <text x="20" y="7" font-size="11" fill="#374151">Mission</text>
        </g>
      </g>`;

    html += `
      <g transform="translate(220, 490)">
        <text x="0" y="0" font-size="13" font-weight="700" fill="#111827">Edge Types</text>
        ${Object.values(edgeStyles).map((style, i) => `
          <g transform="translate(0, ${22 + i * 24})">
            <line x1="0" y1="4" x2="28" y2="4" stroke="${style.stroke}" stroke-width="2" ${style.dash ? `stroke-dasharray="${style.dash}"` : ""}/>
            <text x="34" y="8" font-size="11" fill="#374151">${style.label}</text>
          </g>`).join("")}
      </g>`;

    svg.innerHTML = html;
  }, []);

  return (
    <svg ref={containerRef} id="dependency-graph" className={className} viewBox="0 0 750 650" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
      <rect width="100%" height="100%" fill="#FAFAF8" />
    </svg>
  );
}
