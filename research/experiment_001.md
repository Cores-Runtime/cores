# Experiment Report v1

## Hypothesis

Adaptive scheduling improves mission effectiveness under constrained resources.

## Method

This experiment compares `OperatorSchedulingPolicy`, `EnergyAwarePriorityPolicy`, and `CriticalitySchedulingPolicy` across the deterministic benchmark scenarios, a generated scenario suite, and a seeded Monte Carlo workload.

The evaluation is intentionally held at the scenario level so the scheduler implementation does not change between runs.

The stronger evaluation uses:

- `EnergyAwarePriorityPolicy` as the resource-aware baseline
- a generated scenario suite of 100 samples
- a seeded Monte Carlo study of 1000 trials

Current benchmark sources:

- `benchmarks/run_benchmarks.py`
- `benchmarks/validation.py`
- `benchmarks/evaluation_framework.py`

Current evaluation views:

- legacy mission utility
- revised multi-objective utility score
- energy headroom
- safety coverage
- decision-time cost
- generated scenario averages
- Monte Carlo averages and confidence intervals

The scheduler is frozen. Only the evaluation framework changes between metric definitions.

## Results

### Legacy Mission Utility

| Policy | Nominal Exploration | Low Battery | Sensor Failure | Mean |
|---|---:|---:|---:|---:|
| Priority | 100.0 | 100.0 | 100.0 | 100.0 |
| Criticality | 50.0 | 10.5 | 28.9 | 29.8 |

### Energy Headroom

| Policy | Nominal Exploration | Low Battery | Sensor Failure | Mean |
|---|---:|---:|---:|---:|
| Priority | 17.0 | 0.0 | 17.0 | 11.3 |
| Criticality | 60.0 | 5.0 | 79.0 | 48.0 |

### Safety Coverage

| Policy | Nominal Exploration | Low Battery | Sensor Failure | Mean |
|---|---:|---:|---:|---:|
| Priority | 100.0 | 100.0 | 100.0 | 100.0 |
| Criticality | 100.0 | 100.0 | 100.0 | 100.0 |

### Revised Utility Score

The revised utility score is defined in `research/mission_utility_definition.md`.

The Phase 2A.6 rerun publishes the corresponding score table and graphs from:

- `benchmarks/results/phase_2a6/policy_comparison.csv`
- `benchmarks/results/phase_2a6/component_breakdown.csv`
- `benchmarks/results/phase_2a6/generated_scenario_suite.csv`
- `benchmarks/results/phase_2a6/monte_carlo_trials.csv`
- `benchmarks/results/phase_2a6/utility_score_by_scenario.svg`
- `benchmarks/results/phase_2a6/component_scores_by_scenario.svg`
- `benchmarks/results/phase_2a6/generated_suite_means.svg`
- `benchmarks/results/phase_2a6/monte_carlo_means.svg`

### Expanded Evaluation

The broader Phase 2A.6 evaluation adds:

- a generated scenario suite with 100 samples
- a Monte Carlo evaluation with 1000 trials
- a resource-aware baseline for comparison

Those outputs are the ones that should be used for the publication-grade discussion once the regenerated report is available.

The generated tables and graphs belong in:

- `benchmarks/results/phase_2a6/phase_2a6_evaluation_report.md`
- `benchmarks/results/phase_2a6/generated_suite_means.svg`
- `benchmarks/results/phase_2a6/monte_carlo_means.svg`

## Discussion

Under the legacy completion-oriented metric, the fixed-priority baseline outperforms the adaptive scheduler on mission utility because it executes every mission-tagged module.

That result is not sufficient on its own for a robotics paper, because it does not account for resource feasibility.

The adaptive policy does show a consistent advantage in energy headroom while preserving safety coverage.

The stronger baseline is now important:

- `EnergyAwarePriorityPolicy` checks whether the adaptive policy still clears a more realistic resource-aware comparator.
- the generated scenario suite tests whether the conclusion survives beyond three hand-picked cases.
- the Monte Carlo trial set tests whether the conclusion is stable under randomized battery, hazard, and resource conditions.

That means the current evidence supports a narrower claim:

- adaptive scheduling improves resource preservation
- adaptive scheduling does not yet improve the legacy mission-utility proxy

The revised evaluation framework exists to test whether that conclusion changes when mission utility is defined as a multi-objective robotics score rather than a completion-only proxy.

## Conclusion

Supported?

**Partially supported.**

The deterministic case study supports the claim that adaptive scheduling improves resource preservation under constrained resources.

It does not yet support the stronger claim that adaptive scheduling improves mission utility under the legacy metric.

The broader Phase 2A.6 evaluation should be used to determine whether that conclusion changes once the stronger baseline, the generated scenario suite, and the Monte Carlo workload are included.

The next publication-grade result must come from the Phase 2A.6 rerun under the revised utility definition.
