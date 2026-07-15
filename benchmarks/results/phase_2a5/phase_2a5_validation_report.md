# Phase 2A.5 Validation Report

- Generated: `2026-07-15T13:14:34.321007+00:00`
- Python: `3.11.9`
- Platform: `Windows AMD64`

## Policy Comparison

| Policy | Scenario | Mission Utility (%) | Energy Headroom (%) | Decision Time (ms) | Safety Coverage (%) |
|---|---|---:|---:|---:|---:|
| priority | Scenario A - Nominal Exploration | 100.0 | 17.0 | 0.0292 | 100.0 |
| criticality | Scenario A - Nominal Exploration | 50.0 | 60.0 | 0.2502 | 100.0 |
| risk_aware_knapsack | Scenario A - Nominal Exploration | 50.0 | 60.0 | 0.2960 | 100.0 |
| lexicographic | Scenario A - Nominal Exploration | 52.6 | 59.0 | 0.3390 | 100.0 |
| priority | Scenario B - Low Battery | 100.0 | 0.0 | 0.0132 | 100.0 |
| criticality | Scenario B - Low Battery | 10.5 | 5.0 | 0.1274 | 100.0 |
| risk_aware_knapsack | Scenario B - Low Battery | 10.5 | 5.0 | 0.1684 | 100.0 |
| lexicographic | Scenario B - Low Battery | 28.9 | 0.0 | 0.2168 | 100.0 |
| priority | Scenario C - Obstacle Detected | 100.0 | 17.0 | 0.0121 | 100.0 |
| criticality | Scenario C - Obstacle Detected | 31.6 | 68.0 | 0.1219 | 100.0 |
| risk_aware_knapsack | Scenario C - Obstacle Detected | 31.6 | 68.0 | 0.2059 | 100.0 |
| lexicographic | Scenario C - Obstacle Detected | 50.0 | 69.0 | 0.2462 | 100.0 |
| priority | Scenario D - Emergency Event | 100.0 | 17.0 | 0.0102 | 100.0 |
| criticality | Scenario D - Emergency Event | 50.0 | 60.0 | 0.1146 | 100.0 |
| risk_aware_knapsack | Scenario D - Emergency Event | 50.0 | 60.0 | 0.1856 | 100.0 |
| lexicographic | Scenario D - Emergency Event | 50.0 | 65.0 | 0.2293 | 100.0 |
| priority | Scenario E - Budget Exhaustion | 100.0 | 17.0 | 0.0131 | 100.0 |
| criticality | Scenario E - Budget Exhaustion | 10.5 | 91.0 | 0.1098 | 100.0 |
| risk_aware_knapsack | Scenario E - Budget Exhaustion | 0.0 | 87.0 | 0.1366 | 100.0 |
| lexicographic | Scenario E - Budget Exhaustion | 28.9 | 77.0 | 0.1928 | 100.0 |
| priority | Scenario G - Sensor Failure | 100.0 | 17.0 | 0.0102 | 100.0 |
| criticality | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.1111 | 100.0 |
| risk_aware_knapsack | Scenario G - Sensor Failure | 10.5 | 81.0 | 0.1612 | 50.0 |
| lexicographic | Scenario G - Sensor Failure | 28.9 | 73.0 | 0.2075 | 100.0 |

## Key Findings

- Criticality changed average mission utility across the focused scenarios (Normal, Low Battery, Sensor Failure) by `-70.2%`.
- Criticality changed average energy headroom across the same scenarios by `+36.7%`.
- Safety coverage is reported alongside utility and energy so scheduler gains are not interpreted in isolation.

## Sensitivity Analysis

The safety weight sweep varies `wS` while renormalizing the other weights to keep the total at `1.0`.

| Scenario | wS | Mission Utility (%) | Energy Headroom (%) |
|---|---:|---:|---:|
| Scenario A - Nominal Exploration | 0.20 | 50.0 | 60.0 |
| Scenario B - Low Battery | 0.20 | 10.5 | 5.0 |
| Scenario G - Sensor Failure | 0.20 | 39.5 | 78.0 |
| Scenario A - Nominal Exploration | 0.35 | 50.0 | 60.0 |
| Scenario B - Low Battery | 0.35 | 10.5 | 5.0 |
| Scenario G - Sensor Failure | 0.35 | 28.9 | 79.0 |
| Scenario A - Nominal Exploration | 0.40 | 50.0 | 60.0 |
| Scenario B - Low Battery | 0.40 | 10.5 | 5.0 |
| Scenario G - Sensor Failure | 0.40 | 28.9 | 79.0 |
| Scenario A - Nominal Exploration | 0.60 | 50.0 | 60.0 |
| Scenario B - Low Battery | 0.60 | 10.5 | 5.0 |
| Scenario G - Sensor Failure | 0.60 | 10.5 | 81.0 |

## Ablation Study

Ablations remove one scoring component at a time and renormalize the remaining weights.

| Variant | Scenario | Mission Utility (%) | Energy Headroom (%) | Decision Time (ms) |
|---|---|---:|---:|---:|
| full | Scenario A - Nominal Exploration | 50.0 | 60.0 | 0.0972 |
| full | Scenario B - Low Battery | 10.5 | 5.0 | 0.0972 |
| full | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.1013 |
| no_urgency | Scenario A - Nominal Exploration | 36.8 | 56.0 | 0.1024 |
| no_urgency | Scenario B - Low Battery | 10.5 | 5.0 | 0.0916 |
| no_urgency | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.1026 |
| no_resource_penalty | Scenario A - Nominal Exploration | 50.0 | 60.0 | 0.0951 |
| no_resource_penalty | Scenario B - Low Battery | 10.5 | 5.0 | 0.0915 |
| no_resource_penalty | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.1017 |

## Artifacts

- `policy_comparison.csv`
- `sensitivity_safety_weight.csv`
- `ablation_study.csv`
- `policy_mission_utility.svg`
- `policy_energy_headroom.svg`
- `policy_decision_time.svg`
- `sensitivity_safety_weight.svg`
- `ablation_mission_utility.svg`