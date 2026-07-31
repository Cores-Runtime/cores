# Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Complete | Runtime foundation - cycle, EventBus, priority scheduler |
| 2A | ✅ Complete | Criticality Scheduler |
| 2B | ✅ Complete | Knapsack Scheduler |
| 2A.5 | ✅ Complete | Validation framework - comparison, sensitivity, ablation |
| 2A.6 | ✅ Complete | Multi-objective utility, Monte Carlo evaluation |
| 2C | ✅ Complete | Lexicographic Scheduler + ModuleGraph |
| 3A | ✅ Complete | Runtime Bridge abstraction |
| 3B | ✅ Complete | WebSocket Bridge - live streaming |
| 4B | ✅ Complete | State Estimation - 6 strategies, benchmarks |
| 4F | ✅ Complete | Planning - 5 strategies, mission planner |
| 4G | ✅ Complete | Memory + Logger - episodic/semantic stores, SPSCA consolidation, provenance, full pipeline benchmark |
| Future | 🔄 Planned | Planning Engine (uses memory), wire narratives into planning, Mode Selection, Adaptive Weight Calibration, Operator Module, memory research (confidence calibration, reconsolidation, forgetting) |

## Key Findings

**Experiment 001:** The first adaptive hypothesis was *not* supported under the legacy metric - Criticality scored 29.8% mission utility vs Priority's 100%. Why? Because it was preserving resources, not maximizing throughput. The metric was the problem, not the algorithm.

**Phase 2A.6:** Froze the scheduler, revised the metric to include resource preservation. Added a stronger baseline (EnergyAwarePriorityPolicy).

**Experiment 002:** The Lexicographic scheduler achieves 100% safety coverage in ALL scenarios, fixes the Knapsack's Scenario G regression, improves mission utility in 4/5 constrained scenarios, and executes deterministically in under 1ms.

*This is an honest research project. Hypotheses that fail are documented alongside those that succeed.*
