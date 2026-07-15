# Phase 2A.5 Validation Report

- Generated: `2026-07-15T07:44:59.651622+00:00`
- Python: `3.11.9`
- Platform: `Windows AMD64`

## Policy Comparison

| Policy | Scenario | Mission Utility (%) | Energy Headroom (%) | Decision Time (ms) | Safety Coverage (%) |
|---|---|---:|---:|---:|---:|
| priority | Scenario A - Nominal Exploration | 100.0 | 17.0 | 0.0428 | 100.0 |
| criticality | Scenario A - Nominal Exploration | 50.0 | 60.0 | 0.2462 | 100.0 |
| priority | Scenario B - Low Battery | 100.0 | 0.0 | 0.0193 | 100.0 |
| criticality | Scenario B - Low Battery | 10.5 | 5.0 | 0.1908 | 100.0 |
| priority | Scenario C - Obstacle Detected | 100.0 | 17.0 | 0.0213 | 100.0 |
| criticality | Scenario C - Obstacle Detected | 31.6 | 68.0 | 0.1991 | 100.0 |
| priority | Scenario D - Emergency Event | 100.0 | 17.0 | 0.0140 | 100.0 |
| criticality | Scenario D - Emergency Event | 50.0 | 60.0 | 0.1991 | 100.0 |
| priority | Scenario E - Budget Exhaustion | 100.0 | 17.0 | 0.0153 | 100.0 |
| criticality | Scenario E - Budget Exhaustion | 10.5 | 91.0 | 0.1665 | 100.0 |
| priority | Scenario G - Sensor Failure | 100.0 | 17.0 | 0.0143 | 100.0 |
| criticality | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.1850 | 100.0 |

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
| full | Scenario A - Nominal Exploration | 50.0 | 60.0 | 0.1070 |
| full | Scenario B - Low Battery | 10.5 | 5.0 | 0.1497 |
| full | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.1723 |
| no_urgency | Scenario A - Nominal Exploration | 36.8 | 56.0 | 0.1510 |
| no_urgency | Scenario B - Low Battery | 10.5 | 5.0 | 0.1377 |
| no_urgency | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.1175 |
| no_resource_penalty | Scenario A - Nominal Exploration | 50.0 | 60.0 | 0.1331 |
| no_resource_penalty | Scenario B - Low Battery | 10.5 | 5.0 | 0.1137 |
| no_resource_penalty | Scenario G - Sensor Failure | 28.9 | 79.0 | 0.2016 |

## Artifacts

- `policy_comparison.csv`
- `sensitivity_safety_weight.csv`
- `ablation_study.csv`
- `policy_mission_utility.svg`
- `policy_energy_headroom.svg`
- `policy_decision_time.svg`
- `sensitivity_safety_weight.svg`
- `ablation_mission_utility.svg`