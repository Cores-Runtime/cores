# Phase 2A.5 Discussion

## Scope

This document discusses the current validation model introduced for Phase 2A.5.

It is now superseded by Phase 2A.6, which freezes the scheduler and revises the mission-utility definition without changing the benchmark scenarios.

The numbers below are derived from the current deterministic scenario definitions and scoring model in:

- `benchmarks/run_benchmarks.py`
- `benchmarks/validation.py`

They are intended to answer the current hypothesis with explicit values, not intuition.

## Hypothesis

> Adaptive scheduling improves mission utility compared with fixed priority scheduling.

## Short Answer

No. Under the current validation metric definition, the hypothesis is not supported.

For the three focused scenarios used in the validation discussion:

- Priority Scheduler average mission utility: `100.0%`
- Criticality Scheduler average mission utility: `29.8%`
- Difference: `-70.2 percentage points`

At the same time:

- Priority Scheduler average energy headroom: `11.3%`
- Criticality Scheduler average energy headroom: `48.0%`
- Difference: `+36.7 percentage points`

This means the current adaptive policy preserves substantially more energy headroom, but it does not outperform fixed priority on the currently defined mission-utility metric.

## Focused Scenario Table

| Policy | Scenario | Mission Utility (%) | Energy Headroom (%) | Safety Coverage (%) |
|---|---|---:|---:|---:|
| Priority | Nominal Exploration | 100.0 | 17.0 | 100.0 |
| Priority | Low Battery | 100.0 | 0.0 | 100.0 |
| Priority | Sensor Failure | 100.0 | 17.0 | 100.0 |
| Criticality | Nominal Exploration | 50.0 | 60.0 | 100.0 |
| Criticality | Low Battery | 10.5 | 5.0 | 100.0 |
| Criticality | Sensor Failure | 28.9 | 79.0 | 100.0 |

## Observations

1. The current mission-utility metric strongly favors the Priority Scheduler.

   Because `OperatorSchedulingPolicy` schedules every mission-tagged module, it receives `100%` mission utility in all three focused scenarios, even when the selected workload exceeds the effective energy or time constraints.

2. Criticality improves resource preservation much more than mission utility.

   Relative to Priority Scheduler:

   - Nominal Exploration: energy headroom increased from `17.0%` to `60.0%`
   - Low Battery: energy headroom increased from `0.0%` to `5.0%`
   - Sensor Failure: energy headroom increased from `17.0%` to `79.0%`

3. Safety coverage remained stable in the focused scenarios.

   Both policies achieved `100%` safety coverage for the current required-module sets.

4. The adaptive policy is currently behaving more like a conservation policy than a mission-maximization policy.

   That is a legitimate result, but it does not satisfy the original hypothesis as stated.

## Unexpected Results

### 1. Removing the resource penalty produced almost no change in the focused scenarios

Average mission utility across the focused scenarios:

- Full model: `29.8%`
- No resource penalty: `29.8%`

Under the current scenario definitions, resource-penalty removal did not materially change the selected subsets for the focused comparison set.

That suggests one of two things:

- the current budgets and profiles already force similar selections without the explicit penalty term, or
- the resource penalty is too weakly expressed relative to the other terms in these scenarios.

### 2. Removing urgency changed nominal behavior more than constrained behavior

Average mission utility across the focused scenarios:

- Full model: `29.8%`
- No urgency: `25.4%`

The main drop came from nominal operation:

- Nominal Exploration with urgency: `50.0%`
- Nominal Exploration without urgency: `36.8%`

This is interesting because the urgency term is currently helping preserve some mission work even when no explicit failure or emergency event is present.

### 3. Increasing the safety weight reduces mission utility under the current metric

Average mission utility across the focused scenarios for a safety-weight sweep:

- `wS = 0.20`: `36.8%`
- `wS = 0.35`: `29.8%`
- `wS = 0.40`: `29.8%`
- `wS = 0.60`: `23.7%`

Under the current metric, higher safety weighting pushes selection toward safety-heavy subsets and away from mission-tagged modules, especially in the sensor-failure case.

## Sensitivity Analysis

### Safety weight (`wS`)

| `wS` | Average Mission Utility (%) | Interpretation |
|---:|---:|---|
| 0.20 | 36.8 | Highest mission utility in the current focused set |
| 0.35 | 29.8 | Current hand-tuned default |
| 0.40 | 29.8 | No improvement over current default |
| 0.60 | 23.7 | Significant mission-utility reduction |

This does not prove `wS = 0.35` is optimal. It shows that, under the current metric and current scenario definitions, raising `wS` above the current default is not justified by mission-utility outcomes.

## Limitations

1. Hand-tuned weights

   The current weights are not learned or optimized.

2. Simplified simulator

   The scenarios are deterministic and do not model real sensor noise, actuator lag, or asynchronous disturbances.

3. Static module profiles

   Module costs and mission relevance are fixed descriptors rather than empirical measurements.

4. Current mission-utility metric is incomplete

   Priority Scheduler can score `100%` mission utility even when it ignores effective constraints, because the metric currently measures selected mission relevance but does not penalize infeasible or wasteful schedules.

5. No measured timing values are discussed here

   The current discussion focuses on deterministic utility and energy outcomes. Latency claims should come from generated validation artifacts and benchmark runs, not from handwritten discussion.

## Did We Prove the Hypothesis?

No.

With the current metric definition, the answer is:

- **Hypothesis supported?** `No`
- **Reason:** Fixed priority scored higher mission utility in every focused scenario.

Numerically:

- Nominal Exploration: Criticality `50.0%` vs Priority `100.0%`
- Low Battery: Criticality `10.5%` vs Priority `100.0%`
- Sensor Failure: Criticality `28.9%` vs Priority `100.0%`

The current validation result therefore rejects the hypothesis in its present form.

## What This Actually Tells Us

The current adaptive policy may still be useful, but the evidence says something narrower:

> The current criticality policy preserves substantially more energy headroom while maintaining safety coverage, but it does not improve the currently defined mission-utility metric relative to fixed priority scheduling.

That is still valuable. It means the next research step should focus on the evaluation model before introducing a more complex optimizer.

## Future Work

1. Redefine mission utility so infeasible schedules are penalized.

   If a policy ignores tight energy or time constraints, the utility metric should reflect that rather than awarding a perfect score for selecting everything.

2. Expand sensitivity analysis beyond `wS`.

   The next sweeps should cover:

   - `wM`
   - `wU`
   - `wR`

3. Add more ablations.

   At minimum:

   - no mission term
   - no safety term
   - no mission-context relevance

4. Record actual validation outputs from `benchmarks/validation.py`.

   The report and SVG artifacts should become the canonical source for tables quoted in research notes.

5. Only evaluate Knapsack after the scoring model is stable.

   Otherwise there is no clean way to tell whether any future improvement came from better optimization or from changing the score definition.
