# CORES

**Cognitive Operating Runtime for Embodied Systems**

A robot has one battery, one CPU, and one chance to get home.

CORES is a deterministic, synchronous runtime that decides **which cognitive modules run, in what order, and under what constraints** — every cycle, with provable behavior. It is not the robot's brain. It is the infrastructure that keeps the brain from burning out.

---

## Why CORES?

Autonomous robots run multiple cognitive processes: perception, planning, localization, safety monitoring, fault recovery. In an ideal world, they all run simultaneously. In the real world:

- The battery is finite
- The CPU has a budget
- The mission has a deadline
- The environment is hostile

CORES solves a specific problem: **given finite resources and a changing world, which modules should execute this cycle to maximize mission success without violating safety constraints?**

Think of it as a real-time scheduler, but for cognition rather than processes.

---

## What Makes This Different

| Concern | Typical Approach | CORES |
|---|---|---|
| Scheduling | Priority-based (static) or RTOS (deadline-driven) | **Criticality scoring + multi-objective optimization** |
| Adaptiveness | Fixed policies | **5 policies in progressive complexity**, from trivial to lexicographic Pareto DP |
| Evidence | Anecdotal | **Every claim backed by reproducible benchmarks, ablation studies, and Monte Carlo trials** |
| Safety | Best-effort | **Lexicographic: safety coverage > mission utility > energy > time** |
| Architecture | Monolithic | **Clean strategy pattern with strict component boundaries** |
| Determinism | Non-deterministic | **Fully deterministic — same inputs always produce the same plan** |

---

## Scheduling Policies

CORES implements five policies, each building on the last:

```
Default          →  Run everything, registration order
Priority         →  Fixed priority (human operator baseline)
Criticality      →  Weighted scoring + greedy constraint satisfaction
Knapsack         →  3D DP optimal subset selection
Lexicographic    →  Pareto DP with dependency graph awareness
```

The **Lexicographic Risk-Aware Scheduler** is the current apex: it models inter-module relationships (DEPENDS_ON, REDUNDANT_WITH, MUTUALLY_EXCLUSIVE, SHARES_INFO_WITH) in a typed graph, classifies modules by role (Mandatory → Safety-Critical → Mission → Optional), and solves a lexicographic multi-objective knapsack that guarantees safety coverage first, mission utility second, energy preservation third, and time efficiency last.

---

## Execution Cycle

Every call to `Runtime.step()` runs a deterministic pipeline:

1. **State Estimation** → update robot state (battery, pose, flags)
2. **Event Collection** → flush buffered events from the prior cycle
3. **Planning** → scheduler produces an ordered execution plan
4. **Execution** → modules run in plan order, return results + events
5. **Bridge** → runtime state snapshot published to external consumers
6. **Advance** → cycle count increments

The entire cycle is synchronous, single-threaded, and fully deterministic.

---

## Architecture

```
Runtime (orchestrator)
├── StateEstimator → RobotState
├── EventBus       → internal pub/sub
├── Scheduler
│   ├── SchedulingPolicy
│   │   ├── CriticalityScoringStrategy
│   │   └── ModuleSelectionStrategy
│   └── (Pluggable: 5 implementations)
├── ExecutionLayer → module execute()
├── RuntimeBridge  → snapshot transport
│   ├── InMemoryRuntimeBridge
│   └── WebSocketRuntimeBridge → JSON stream
└── Modules        → user-defined cognitive processes
```

**Design invariants:**
- `RobotState` is the single source of truth
- Only the scheduler produces execution plans
- Only the execution layer invokes modules
- The event bus knows nothing about other components
- The bridge is the only boundary between runtime internals and external consumers

---

## Current Status

| Phase | Status | What |
|---|---|---|
| 1 | Complete | Core runtime: cycle, EventBus, priority scheduler |
| 2A (Step 2) | Complete | CriticalitySchedulingPolicy |
| 2B (Step 3) | Complete | RiskAwareKnapsackSchedulingPolicy |
| 2A.5 | Complete | Validation: comparison, sensitivity, ablation |
| 2A.6 | Complete | Revised multi-objective utility, Monte Carlo evaluation |
| 2C | Complete | LexicographicRiskAwareSchedulingPolicy + ModuleGraph |
| 3A | Complete | RuntimeBridge abstraction + InMemoryRuntimeBridge |
| 3B | Complete | WebSocketRuntimeBridge — live streaming to clients |
| Future | Planned | Mode Selection Layer, Adaptive Weight Calibration, Operator Cognitive Module |

---

## Quick Start

```bash
cd cores/

# Install dependencies
pip install pydantic frozendict websockets

# Run tests
python -m pytest

# Run benchmarks
python benchmarks/run_benchmarks.py

# Run validation pipeline
python benchmarks/validation.py

# Run evaluation framework
python benchmarks/evaluation_framework.py
```

---

## Key Findings (from research)

**Experiment 001:** The first adaptive hypothesis was *not* supported under the legacy metric — Criticality scored 29.8% mission utility vs Priority's 100%. Why? Because it was preserving resources, not maximizing throughput. The metric was the problem, not the algorithm.

**Phase 2A.6:** Froze the scheduler, revised the metric to include resource preservation. Added a stronger baseline (EnergyAwarePriorityPolicy).

**Experiment 002:** The Lexicographic scheduler achieves 100% safety coverage in ALL scenarios, fixes the Knapsack's Scenario G regression, improves mission utility in 4/5 constrained scenarios, and executes deterministically in under 1ms.

**This is an honest research project.** Hypotheses that fail are documented alongside those that succeed.

---

## Key Documents

- [Research Design](research/adaptive_scheduler_design.md) — formal mathematical formulation
- [Experiment 001](research/experiment/experiment_001.md) — adaptive scheduling evaluation
- [Experiment 002](research/experiment/experiment_002.md) — lexicographic scheduler results
- [Architecture](docs/architecture.md) — component boundaries and invariants
- [Commands](docs/commands.md) — full command reference

---

## License

Apache 2.0
