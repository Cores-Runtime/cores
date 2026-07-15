# Phase 2A.6 Evaluation Framework

- Generated: `2026-07-15T07:48:26.691746+00:00`
- Python: `3.11.9`
- Platform: `Windows AMD64`

## Purpose

Re-run the existing benchmark scenarios without modifying the scheduler implementation, but under a revised multi-objective mission-utility definition.

## Scalar Utility Weights

| Component | Weight |
|---|---:|
| completion | 0.35 |
| safety | 0.20 |
| energy | 0.15 |
| time | 0.15 |
| preservation | 0.15 |

## Scenario Comparison

| Policy | Scenario | Utility Score (%) | Legacy Utility (%) | Completion (%) | Safety (%) | Energy (%) | Time (%) | Preservation (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| priority | Scenario A - Nominal Exploration | 58.4 | 100.0 | 100.0 | 100.0 | 17.0 | 0.0 | 5.7 |
| criticality | Scenario A - Nominal Exploration | 55.0 | 50.0 | 50.0 | 100.0 | 60.0 | 27.0 | 30.0 |
| priority | Scenario B - Low Battery | 55.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 |
| criticality | Scenario B - Low Battery | 40.0 | 10.5 | 10.5 | 100.0 | 5.0 | 64.0 | 39.7 |
| priority | Scenario C - Obstacle Detected | 58.4 | 100.0 | 100.0 | 100.0 | 17.0 | 0.0 | 5.7 |
| criticality | Scenario C - Obstacle Detected | 46.0 | 31.6 | 31.6 | 100.0 | 68.0 | 1.7 | 30.2 |
| priority | Scenario D - Emergency Event | 58.4 | 100.0 | 100.0 | 100.0 | 17.0 | 0.0 | 5.7 |
| criticality | Scenario D - Emergency Event | 55.0 | 50.0 | 50.0 | 100.0 | 60.0 | 27.0 | 30.0 |
| priority | Scenario E - Budget Exhaustion | 58.4 | 100.0 | 100.0 | 100.0 | 17.0 | 0.0 | 5.7 |
| criticality | Scenario E - Budget Exhaustion | 46.1 | 10.5 | 10.5 | 100.0 | 91.0 | 15.0 | 43.1 |
| priority | Scenario G - Sensor Failure | 58.4 | 100.0 | 100.0 | 100.0 | 17.0 | 0.0 | 5.7 |
| criticality | Scenario G - Sensor Failure | 46.5 | 28.9 | 28.9 | 100.0 | 79.0 | 0.0 | 30.2 |

## Interpretation

The revised metric is designed to answer whether a schedule is good for autonomous operation, not merely whether it selected mission-tagged modules.

The report should be read by comparing utility-score changes against the legacy mission-utility column.

## Focused Takeaways

- Average legacy utility: priority `100.0%`, criticality `29.8%`.
- Average revised utility score: priority `57.3%`, criticality `47.2%`.

## Artifacts

- `policy_comparison.csv`
- `component_breakdown.csv`
- `utility_score_by_scenario.svg`
- `component_scores_by_scenario.svg`