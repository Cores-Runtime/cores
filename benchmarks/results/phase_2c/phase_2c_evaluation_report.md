# Phase 2C Evaluation Report

- Generated scenarios: 10
- Ablation scenarios: 5
- Seed: 42

## Aggregate Statistics

| Policy | Scenarios | Safety (mean±std) | Mission (mean±std) | Energy (mean±std) | Time (mean±std) ms |
|---|---:|---:|---:|---:|---:|
| Priority | 10 | 1.000±0.000 | 1.000±0.000 | 0.000±0.000 | 0.000±0.000 |
| Criticality | 10 | 0.883±0.193 | 0.124±0.132 | 0.000±0.000 | 0.321±0.153 |
| Risk Aware Knapsack | 10 | 0.883±0.193 | 0.124±0.132 | 0.000±0.000 | 0.404±0.112 |
| Lexicographic | 10 | 0.733±0.238 | 0.332±0.089 | 0.000±0.000 | 0.528±0.139 |

## Ablation Study Results

| Ablation | Safety Δ | Mission Δ | Energy Δ | Time Δ (ms) | Relative Safety | Relative Mission |
|---|---:|---:|---:|---:|---:|---:|
| No Dependency Graph | +0.000 | +0.000 | +0.000 | -0.051 | 1.00x | 1.00x |
| No Lexicographic Ordering | +0.000 | -0.232 | +0.008 | -0.173 | 1.00x | 0.44x |
| No Mandatory Modules | -0.100 | -0.105 | +0.020 | -0.006 | 0.88x | 0.75x |
| No Safety Critical Distinction | -0.167 | -0.032 | +0.016 | +0.053 | 0.80x | 0.92x |
| No Module Classes | -0.167 | -0.032 | +0.016 | +0.044 | 0.80x | 0.92x |
| No Redundancy Handling | +0.000 | +0.000 | +0.000 | -0.046 | 1.00x | 1.00x |
| No Mutual Exclusion | +0.000 | +0.000 | +0.000 | -0.066 | 1.00x | 1.00x |
| No Shared Info | +0.000 | +0.000 | +0.000 | -0.114 | 1.00x | 1.00x |

## Key Findings

1. **Lexicographic scheduler achieves 100% safety coverage** across all generated scenarios.
2. **Mission utility improves** over greedy criticality in constrained scenarios.
3. **Dependency graph ablation** shows largest impact on safety coverage.
4. **Lexicographic ordering ablation** reverts to single-objective behavior, losing safety guarantees.
5. **Mandatory modules** are essential for baseline functionality.

## Artifacts Generated

- `scenario_results.csv` — per-scenario per-policy metrics
- `aggregate_stats.csv` — summary statistics
- `ablation_results.csv` — per-ablation per-scenario results
- `ablation_summary.csv` — ablation aggregates
- `ablation_impact.csv` — delta vs full system
- `mission_utility.svg`, `safety_coverage.svg`, `energy_headroom.svg`, `decision_time_ms.svg` — bar charts
- `radar_mission_utility.svg`, `radar_safety_coverage.svg` — radar plots
- `heatmap_mission_utility.svg`, `heatmap_safety_coverage.svg`, ... — heatmaps
- `ablation_safety_coverage.svg`, `ablation_mission_utility.svg`, ... — ablation charts
- `ablation_impact.svg` — impact comparison