export const radars = [
  {
    title: "Radar: Mission Utility Across Scenarios",
    desc: "20-axis radar plot. Lexicographic (amber) dominates in constrained quadrants.",
    color: "amber",
  },
  {
    title: "Radar: Safety Coverage Across Scenarios", 
    desc: "Lexicographic (emerald) achieves full coverage. Knapsack (violet) drops in Sensor Failure.",
    color: "emerald",
  },
];

export const heatmaps = [
  {
    title: "Heatmap: Mission Utility",
    desc: "Policy × Scenario matrix. Darker = higher utility. Lexicographic column leads in constrained rows.",
    color: "amber",
  },
  {
    title: "Heatmap: Safety Coverage",
    desc: "Lexicographic row is solid green. Knapsack shows red in Sensor Failure column.",
    color: "emerald",
  },
  {
    title: "Heatmap: Energy Headroom",
    desc: "Energy preservation patterns. Priority wastes energy (no budget awareness). Lexicographic balances.",
    color: "blue",
  },
  {
    title: "Heatmap: Decision Time",
    desc: "All sub-millisecond. Lexicographic slightly higher (Pareto DP) but deterministic.",
    color: "violet",
  },
];