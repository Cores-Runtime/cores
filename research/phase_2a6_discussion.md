# Phase 2A.6 Discussion

## Scope

This document is the discussion companion to `phase_2a6_evaluation_framework.md`.

Its job is to interpret the rerun benchmarks under the revised multi-objective mission-utility definition.

## What Should Be Compared

For each benchmark scenario, compare:

- legacy mission utility
- revised utility score
- component breakdown

The key question is whether the earlier conclusion changes once resource feasibility is part of the metric.

The revised evaluation also compares against `EnergyAwarePriorityPolicy` and includes a generated scenario suite plus a seeded Monte Carlo workload.

## What Counts as a Changed Conclusion

The conclusion changes if the revised utility score materially alters the ranking between:

- `OperatorSchedulingPolicy`
- `CriticalitySchedulingPolicy`

in one or more representative scenarios.

## Interpretation Rules

1. If the revised metric still favors the baseline, the original hypothesis is not supported.
2. If the revised metric favors the adaptive policy under constrained scenarios, that is evidence that the earlier completion-only metric was too weak.
3. If the revised metric reverses the conclusion only because of one component, the evaluation should inspect that component directly.

## Publication Requirement

This section should be populated from the generated report in `benchmarks/results/phase_2a6/phase_2a6_evaluation_report.md`.

Do not cite the legacy metric alone.

The publication-grade conclusion should state both:

- whether the conclusion changed
- why it changed
