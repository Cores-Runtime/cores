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

## The State Estimation — Physical Understanding & Prediction (Phase 4B)

CORES now includes a **cognitive node for physical reality**: the State Estimation. It continuously executes a 10-step cognitive loop (Observe → Associate → Fuse → Update → Predict → Reason → Check Consistency → Manage Confidence → Explain → Publish) and maintains an evolving understanding of the world.

```
StateEstimation
├── ObservationAssociation    — match sensor observations to tracked objects via spatial proximity
├── SensorFusion              — confidence-weighted multi-sensor fusion
├── PhysicalReasoning         — causal motion classification (stationary, constant velocity, external force, gravity)
├── ConsistencyChecker        — detect self-detections, impossible speeds, overlaps, temporal anomalies
├── ConfidenceManager         — decay/boost belief confidence over time
├── Explainability Engine     — human-readable understanding summary
└── WorldModelStrategy        — 6 pluggable physical reasoning backends
```

**Every heuristic is a configurable candidate model**

### World Model Strategies

All strategies implement the `WorldModelStrategy` ABC and are interchangeable at runtime:

| Strategy | File | Specialty |
|---|---|---|
| **SimpleObjectRegistry** | `simple_registry.py` | Baseline — flat list, no spatial/kinematic reasoning |
| **OccupancyGrid** | `occupancy_grid.py` | Classic log-odds grid with free/occupied cells |
| **SemanticWorldModel** | `semantic.py` | Knowledge graph with typed nodes and relations |
| **ProbabilisticWorldModel** | `probabilistic.py` | Bayesian belief tracking with per-object variance |
| **DynamicTrackingWorldModel** | `dynamic_tracking.py` | Kalman filter (4x4 covariance, constant-velocity) |
| **SSKPM** | `sskpm.py` | 9-DOF kinematic + spatial chunk indexing + Bayesian fusion |

### Benchmark Results (head-to-head)

| Metric | Best | Value | Runner-Up |
|---|---|---|---|
| Update latency | SemanticWorldModel | 1,625 µs | Probabilistic (1,985 µs) |
| Lookup latency | OccupancyGrid | 49 µs | SimpleObjectRegistry (618 µs) |
| Tracking accuracy | **SSKPM** | **0.431 mean error** | DynamicTracking (0.460) |
| Prediction error | DynamicTracking | **0.163** | SSKPM (0.332) |
| Serialized size | SimpleObjectRegistry | 19.3 KB | DynamicTracking (29.2 KB) |
| Runtime integration | SimpleObjectRegistry | 249 µs/step | SemanticWorldModel (275 µs) |

**Key insight**: No single strategy dominates. SSKPM wins on tracking accuracy (full 9-DOF kinematics), DynamicTracking wins on prediction (Kalman filter), Semantic is fastest for updates. The simple baseline remains competitive on most metrics.

Default strategy is `SimpleObjectRegistry` (backward compatible). Switch to `SSKPM` for best accuracy:

```python
runtime = Runtime(scheduler, execution_layer, world_model=SSKPM())
```

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
├── StateEstimator   → RobotState
├── EventBus         → internal pub/sub
├── Scheduler
│   ├── SchedulingPolicy
│   │   ├── CriticalityScoringStrategy
│   │   └── ModuleSelectionStrategy
│   └── (Pluggable: 5 implementations)
├── ExecutionLayer   → module execute()
├── StateEstimation        → cognitive node: physical understanding
│   ├── ObservationAssociation
│   ├── SensorFusion
│   ├── PhysicalReasoning
│   ├── ConsistencyChecker
│   ├── ConfidenceManager
│   └── WorldModelStrategy (6 implementations)
├── RuntimeBridge    → snapshot transport
│   ├── InMemoryRuntimeBridge
│   └── WebSocketRuntimeBridge → JSON stream
└── Modules          → user-defined cognitive processes
```

**Design invariants:**
- `RobotState` is the single source of truth
- Only the scheduler produces execution plans
- Only the execution layer invokes modules
- The event bus knows nothing about other components
- The State Estimation owns all physical understanding — modules read `context.world_model`
- The bridge is the only boundary between runtime internals and external consumers

---

## Current Status

| Phase | Status | What |
|---|---|---|---|
| 1 | Complete | Core runtime: cycle, EventBus, priority scheduler |
| 2A (Step 2) | Complete | CriticalitySchedulingPolicy |
| 2B (Step 3) | Complete | RiskAwareKnapsackSchedulingPolicy |
| 2A.5 | Complete | Validation: comparison, sensitivity, ablation |
| 2A.6 | Complete | Revised multi-objective utility, Monte Carlo evaluation |
| 2C | Complete | LexicographicRiskAwareSchedulingPolicy + ModuleGraph |
| 3A | Complete | RuntimeBridge abstraction + InMemoryRuntimeBridge |
| 3B | Complete | WebSocketRuntimeBridge — live streaming to clients |
| **4B** | **Complete** | **State Estimation cognitive node + 6 WorldModelStrategies + benchmarks** |
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
- [State Estimation & World Modeling](research/phase-4b-state-estimation.md) — Phase 4B research, architecture, benchmark results
- [Architecture](docs/architecture.md) — component boundaries and invariants
- [Commands](docs/commands.md) — full command reference


---

## License

Apache 2.0
