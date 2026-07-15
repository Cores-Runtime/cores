# Phase 2A.6 — Evaluation Framework

## Objective

Phase 2A.6 freezes the scheduler implementation and changes only the evaluation framework.

The goal is to answer a narrower and more defensible question:

> If the scheduler is held fixed, does the conclusion about its quality change when mission utility is defined as a multi-objective robotics score instead of a completion-only proxy?

## Goals

1. Formally define mission utility.
2. Justify why the definition is appropriate for autonomous robotics.
3. Re-run all existing benchmark scenarios under the revised metric.
4. Compare the revised metric with the legacy completion-only metric.
5. Compare against a stronger resource-aware baseline.
6. Run a generated scenario suite and a Monte Carlo evaluation.
7. Determine whether the adaptive scheduler still outperforms the baselines.

## Inputs

The evaluation framework reuses the existing benchmark scenario set from `benchmarks/run_benchmarks.py`.

No scheduler logic changes are introduced.

A stronger baseline is included for comparison:

- `EnergyAwarePriorityPolicy`

The scheduler itself remains frozen.

## Method

The evaluation framework computes two metrics for every policy and scenario:

1. Legacy mission utility
2. Revised multi-objective utility score

The revised score is documented in `research/mission_utility_definition.md` and combines:

- mission completion
- safety coverage
- energy headroom
- time headroom
- resource preservation

## Outputs

The framework writes:

- policy comparison CSV
- component breakdown CSV
- generated scenario suite CSV
- Monte Carlo trial CSV
- utility-score chart
- component-score chart
- generated-suite mean chart
- Monte Carlo mean chart
- evaluation report

## Interpretation Rule

The revised metric is only valid if it is applied consistently to every policy and every benchmark scenario.

If the conclusions change after the rerun, that is a result, not a failure.

The point of this milestone is to distinguish:

- improvement due to the scheduler
- improvement or degradation due to the metric definition

## Success Criteria

Phase 2A.6 is complete when:

- mission utility is formally defined
- the benchmark suite is rerun with the revised metric
- the report states whether the earlier conclusion still holds
- the scheduler itself remains unchanged
