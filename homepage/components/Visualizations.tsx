"use client";

import { motion } from "framer-motion";
import { BarChart } from "@/components/charts/BarChart";
import { RadarChart } from "@/components/charts/RadarChart";
import { HeatmapChart } from "@/components/charts/HeatmapChart";
import { ParetoChart } from "@/components/charts/ParetoChart";
import { DependencyGraph } from "@/components/charts/DependencyGraph";
import { benchmarkData, radarData, heatmapData } from "@/lib/benchmark-data";

export function Visualizations() {
  const chartConfigs = [
    {
      id: "mission_utility",
      title: "Mission Utility by Scenario",
      desc: "Grouped bar chart across all 20 scenario types. Lexicographic (amber) leads in constrained scenarios.",
    },
    {
      id: "safety_coverage",
      title: "Safety Coverage by Scenario",
      desc: "Lexicographic maintains 100% safety coverage. Knapsack drops to 50% in Sensor Failure.",
    },
    {
      id: "energy_headroom",
      title: "Energy Headroom by Scenario",
      desc: "Energy preservation under tight budgets. Lexicographic beats Criticality in Budget Exhaustion.",
    },
    {
      id: "decision_time",
      title: "Decision Time by Scenario",
      desc: "All policies under 1ms. Lexicographic ~0.5ms (3D Pareto DP). Well within real-time bounds.",
    },
  ];

  const radarConfigs = [
    {
      id: "mission_utility",
      title: "Radar: Mission Utility Across Scenarios",
      desc: "20-axis radar plot. Lexicographic (amber) dominates in constrained quadrants.",
      color: "amber",
    },
    {
      id: "safety_coverage",
      title: "Radar: Safety Coverage Across Scenarios",
      desc: "Lexicographic (emerald) achieves full coverage. Knapsack (violet) drops in Sensor Failure.",
      color: "emerald",
    },
  ];

  const heatmapConfigs = [
    {
      id: "mission_utility",
      title: "Heatmap: Mission Utility",
      desc: "Policy × Scenario matrix. Darker = higher utility. Lexicographic column leads in constrained rows.",
      color: "amber",
    },
    {
      id: "safety_coverage",
      title: "Heatmap: Safety Coverage",
      desc: "Lexicographic row is solid green. Knapsack shows red in Sensor Failure column.",
      color: "emerald",
    },
    {
      id: "energy_headroom",
      title: "Heatmap: Energy Headroom",
      desc: "Energy preservation patterns. Priority wastes energy (no budget awareness). Lexicographic balances.",
      color: "blue",
    },
    {
      id: "decision_time",
      title: "Heatmap: Decision Time",
      desc: "All sub-millisecond. Lexicographic slightly higher (Pareto DP) but deterministic.",
      color: "violet",
    },
  ];

  return (
    <section
      id="visualizations"
      className="py-24 px-6 bg-paper"
      aria-labelledby="viz-heading"
    >
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="inline-block px-3 py-1 rounded-full bg-accent/10 text-accent text-sm font-medium mb-4">
            Visual Evidence
          </span>
          <h2 id="viz-heading" className="text-4xl md:text-5xl font-bold text-ink mb-4 text-balance">
            Charts That Communicate
          </h2>
          <p className="text-lg text-muted max-w-2xl mx-auto text-balance">
            Generated as SVG — infinite resolution, version-controllable, embeddable anywhere.
            No external charting libraries. Pure, deterministic output.
          </p>
        </motion.div>

        <div className="space-y-16">
          {/* Bar Charts */}
          {chartConfigs.map((chart, index) => (
            <motion.div
              key={chart.id}
              className="card p-6 md:p-8"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: index * 0.1 }}
            >
              <div className="mb-6">
                <h3 className="text-xl font-bold text-ink mb-2">{chart.title}</h3>
                <p className="text-muted">{chart.desc}</p>
              </div>
              <BarChart
                id={chart.id}
                data={benchmarkData}
                metric={chart.id === "mission_utility" ? "missionUtility" : chart.id === "safety_coverage" ? "safetyCoverage" : chart.id === "energy_headroom" ? "energyHeadroom" : "decisionTimeMs"}
                className="w-full aspect-video md:aspect-[16/9]"
              />
            </motion.div>
          ))}

          {/* Radar Charts */}
          {radarConfigs.map((chart, index) => (
            <motion.div
              key={chart.id}
              className="card p-6 md:p-8"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: index * 0.1 }}
            >
              <div className="mb-6">
                <h3 className="text-xl font-bold text-ink mb-2">{chart.title}</h3>
                <p className="text-muted">{chart.desc}</p>
              </div>
              <RadarChart
                id={chart.id}
                data={radarData}
                color={chart.color}
                className="w-full max-w-md mx-auto aspect-square"
              />
            </motion.div>
          ))}

          {/* Heatmaps */}
          {heatmapConfigs.map((chart, index) => (
            <motion.div
              key={chart.id}
              className="card p-6 md:p-8"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: index * 0.08 }}
            >
              <div className="mb-6">
                <h3 className="text-xl font-bold text-ink mb-2">{chart.title}</h3>
                <p className="text-muted">{chart.desc}</p>
              </div>
              <HeatmapChart
                id={chart.id}
                data={heatmapData}
                color={chart.color}
                className="w-full aspect-square"
              />
            </motion.div>
          ))}

          {/* Pareto Frontier */}
          <motion.div
            className="card p-8"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h3 className="text-2xl font-bold text-ink mb-6 text-center">Pareto Frontier: Safety vs Mission</h3>
            <p className="text-muted text-center mb-8 max-w-2xl mx-auto">
              Each point is a scheduler configuration. The Pareto frontier (connected line) shows
              the optimal trade-off curve. Lexicographic operates at the knee — maximum safety
              for maximum mission utility.
            </p>
            <ParetoChart className="w-full aspect-square" />
          </motion.div>

          {/* Dependency Graph */}
          <motion.div
            className="card p-8"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h3 className="text-2xl font-bold text-ink mb-6 text-center">Module Dependency Graph</h3>
            <DependencyGraph
              className="w-full aspect-[4/3]"
            />
          </motion.div>
        </div>
      </div>
    </section>
  );
}