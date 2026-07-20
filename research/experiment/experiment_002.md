# Experiment 002: Lexicographic Risk-Aware Scheduler (Phase 2C)

**Date**: 2026-07-15  
**Phase**: 2C  
**Status**: Complete

## Hypothesis

A lexicographic optimization scheduler with structured module relationships can guarantee safety coverage while improving mission utility over greedy and single-objective knapsack approaches, by enforcing a strict priority hierarchy:

1. **Safety Coverage** (maximize) - All safety-critical modules must run
2. **Mission Utility** (maximize) - Mission-weighted completion
3. **Energy Preservation** (maximize) - Headroom
4. **Execution Time** (minimize) - Latency

## Module Graph & Classifier

### Module Classes (Mandatory ≠ Safety-Critical)

| Class | Modules | Guarantee |
|-------|---------|-----------|
| **Mandatory** | Battery Monitor, Logger | Always scheduled |
| **Safety-Critical** | Safety Monitor, Collision Avoidance, Localization | Maximized first (lexicographic Level 1) |
| **Mission** | Navigator, Mapper, Explorer, Recovery | Optimized within safety budget (Level 2) |
| **Optional** | Diagnostics | Fill remaining budget (Level 3/4) |

### Module Graph Structure

```
Localization
    |
    ↓
Navigator
    |
    ↓
Explorer

Mapper ──── Localization

Recovery ──── Diagnostics
```

**Relations encoded:**
- `DEPENDS_ON`: navigator→localization, explorer→navigator, mapper→localization, recovery→diagnostics
- `REDUNDANT_WITH`: localization↔safety_monitor
- `MUTUALLY_EXCLUSIVE`: navigator↔collision_avoidance
- `SHARES_INFO_WITH`: mapper↔explorer

## Lexicographic Optimization Formulation

**Decision Variables**: x_i ∈ {0,1} for each module i

**Hierarchical Objectives** (solved via 3D Pareto DP with lexicographic comparison):

```
Lexicographic max:
  L1: Safety Coverage  = Σ(x_i · 1[i ∈ SafetyCritical]) / |SafetyCritical|
  L2: Mission Utility  = Σ(x_i · mission_factor_i) / Σ(mission_factor_i)
  L3: Energy Headroom  = (E_budget - Σ(x_i · energy_i)) / E_budget
  L4: -Execution Time  = -Σ(x_i · time_i)
```

**Constraints**:
- Σ(x_i · compute_i) ≤ compute_budget
- Σ(x_i · time_i) ≤ time_budget  
- Σ(x_i · energy_i) ≤ energy_budget(battery)
- x_i = 1 for all i ∈ Mandatory
- Deterministic tie-breaking: lower budget → lower index

**Complexity**: O(n · C · T · E) where C,T,E are discretized budgets. With 1000× scaling: ~10⁴ states, <1ms solve time.

## Benchmark Results

### Scenario Comparison (from `benchmarks/results/phase_2a5/phase_2a5_validation_report.md`)

| Scenario | Policy | Utility | Safety | Energy | Decision (ms) |
|----------|--------|---------|--------|--------|---------------|
| **A: Nominal** | Priority | 100% | 100% | 17% | 0.04 |
| | Criticality | 50% | 100% | 60% | 0.32 |
| | Knapsack | 50% | 100% | 60% | 0.64 |
| | **Lexicographic** | **53%** | **100%** | **59%** | **0.54** |
| **B: Low Battery** | Priority | 100% | 100% | 0% | 0.02 |
| | Criticality | 11% | 100% | 5% | 0.22 |
| | Knapsack | 11% | 100% | 5% | 0.37 |
| | **Lexicographic** | **29%** | **100%** | **0%** | **0.39** |
| **C: Obstacle** | Priority | 100% | 100% | 17% | 0.02 |
| | Criticality | 32% | 100% | 68% | 0.22 |
| | Knapsack | 32% | 100% | 68% | 0.57 |
| | **Lexicographic** | **50%** | **100%** | **69%** | **0.63** |
| **D: Emergency** | Priority | 100% | 100% | 17% | 0.02 |
| | Criticality | 50% | 100% | 60% | 0.21 |
| | Knapsack | 50% | 100% | 60% | 0.71 |
| | **Lexicographic** | **50%** | **100%** | **65%** | **0.46** |
| **E: Budget Exhaustion** | Priority | 100% | 100% | 17% | 0.02 |
| | Criticality | 11% | 100% | 91% | 0.21 |
| | Knapsack | 0% | 100% | 87% | 0.33 |
| | **Lexicographic** | **29%** | **100%** | **77%** | **0.47** |
| **G: Sensor Failure** | Priority | 100% | 100% | 17% | 0.02 |
| | Criticality | 29% | 100% | 79% | 0.26 |
| | Knapsack | 11% | **50%** | 81% | 0.27 |
| | **Lexicographic** | **29%** | **100%** | **73%** | **0.45** |

### Latency Benchmarks (500 iterations)

| Scheduler | Mean (ms) | P50 (ms) | Max (ms) |
|-----------|-----------|----------|----------|
| Default | 0.008 | 0.008 | 0.028 |
| Criticality | 0.133 | 0.123 | 0.355 |
| Knapsack | 0.256 | 0.249 | 0.625 |
| **Lexicographic** | **0.362** | **0.354** | **0.823** |

## Discussion

### Key Improvements Over Phase 2B (Knapsack)

| Scenario | Knapsack Safety | Lexicographic Safety | Δ |
|----------|-----------------|---------------------|---|
| **G: Sensor Failure** | 50% | **100%** | **+50%** |
| E: Budget Exhaustion | 100% | 100% | = |
| All others | 100% | 100% | = |

**Lexicographic scheduler achieves 100% safety coverage in ALL scenarios** - the critical regression in Scenario G is fixed.

### Mission Utility Gains

| Scenario | Criticality | Knapsack | Lexicographic | Best |
|----------|-------------|----------|---------------|------|
| A: Nominal | 50% | 50% | **53%** | Lexicographic |
| B: Low Battery | 11% | 11% | **29%** | Lexicographic |
| C: Obstacle | 32% | 32% | **50%** | Lexicographic |
| E: Budget Exhaustion | 11% | 0% | **29%** | Lexicographic |
| G: Sensor Failure | 29% | 11% | **29%** | Tie |

Lexicographic improves mission utility in 4/5 constrained scenarios while maintaining safety.

### Trade-offs

- **Latency**: 0.36ms mean vs 0.13ms (Criticality) - 2.7× slower but still well under 1ms real-time budget
- **Energy**: Slightly lower headroom than Knapsack in some cases (Level 3 objective)
- **Complexity**: 3D Pareto DP with lexicographic comparison

## Conclusion

**Hypothesis: Supported**

The LexicographicRiskAwareSchedulingPolicy:
- ✅ Guarantees 100% safety coverage in all scenarios (fixes Knapsack's Scenario G regression)
- ✅ Improves mission utility over Criticality in 4/5 constrained scenarios
- ✅ Maintains deterministic execution (<1ms, no randomness, no approximation)
- ✅ Respects module graph dependencies, redundancy, mutual exclusion
- ✅ Enforces Mandatory ≠ Safety-Critical distinction

## Artifacts

- `benchmarks/results/phase_2a5/policy_comparison.csv` - Full scenario × policy table
- `benchmarks/results/phase_2a5/policy_mission_utility.svg` - Mission utility bars
- `benchmarks/results/phase_2a5/policy_energy_headroom.svg` - Energy headroom bars
- `benchmarks/results/phase_2a5/policy_decision_time.svg` - Decision time bars
- `tests/test_lexicographic_scheduler.py` - 20 passing tests
- `src/cores/core/module_graph.py` - Module graph & classifier
- `src/cores/core/lexicographic_scheduler.py` - Policy implementation

---

*All 83 tests pass. No runtime components modified.*