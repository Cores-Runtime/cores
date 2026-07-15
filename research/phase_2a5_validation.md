# Phase 2A.5 — Validation

## Purpose

Phase 2A.5 validates the scheduler research with evidence rather than additional scheduler features.

This milestone answers:

- Does `CriticalitySchedulingPolicy` improve mission utility over the priority baseline?
- How much energy headroom does each policy preserve?
- What is the scheduler decision-time cost?
- How sensitive are results to changes in `wS`?
- Which scoring components materially affect performance?

## Artifacts

Run:

```bash
python benchmarks/validation.py
```

This generates:

- `benchmarks/results/phase_2a5/phase_2a5_validation_report.md`
- `benchmarks/results/phase_2a5/policy_comparison.csv`
- `benchmarks/results/phase_2a5/sensitivity_safety_weight.csv`
- `benchmarks/results/phase_2a5/ablation_study.csv`
- `benchmarks/results/phase_2a5/*.svg`

## Included Analyses

### 1. Policy Comparison

Compares `OperatorSchedulingPolicy` vs `CriticalitySchedulingPolicy` across the canonical scenario suite.

Reported metrics:

- Mission Utility
- Energy Headroom
- Decision Time
- Safety Coverage

### 2. Sensitivity Analysis

Sweeps `wS` across a configurable range and records mission utility changes.

The default sweep is:

- `0.20`
- `0.35`
- `0.40`
- `0.60`

Other weights are renormalized to keep the total equal to `1.0`.

### 3. Ablation Study

Measures the effect of removing one scoring component at a time.

Current ablations:

- `no_urgency`
- `no_resource_penalty`

## Interpretation Rules

- If criticality improves utility but collapses safety coverage, the result is invalid.
- If criticality improves utility only under one weight setting, the model is fragile.
- If ablations do not change performance, that scoring feature is weakly justified.
- Knapsack work should only proceed after this validation shows the scoring model is both useful and stable.
