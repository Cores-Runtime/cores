# Phase 4B: Dynamic World Modeling

## Architecture Migration

The WorldModel hierarchy was migrated from a standalone runtime subsystem to the internal
reasoning engine of the **Physicist** cognitive node.

### Before

```
Runtime
  └── WorldModel  (standalone subsystem)
```

### After

```
Runtime
  └── Physicist  (cognitive module)
        ├── WorldModelStrategy  (reasoning engine)
        │     ├── SimpleObjectRegistry
        │     ├── OccupancyGrid
        │     ├── SemanticWorldModel
        │     ├── ProbabilisticWorldModel
        │     ├── DynamicTrackingWorldModel
        │     └── SSKPM
        │
        ├── Belief Manager
        ├── Consistency Checker
        ├── Confidence Manager
        └── Explainability Engine
```

The `WorldModel` ABC was renamed to `WorldModelStrategy` (with a backward-compatible
`WorldModel` alias) to reflect that it is a *physical reasoning strategy* used by the
Physicist, not a standalone runtime subsystem.

### Heuristic Parameters vs Runtime Config

The Physicist separates **heuristic parameters** (temporary thresholds for
rule-based sub-components) from **runtime configuration** (permanent structural
options like logging or sensor config).

Each sub-component has its own parameter dataclass (e.g.
`AssociationParameters`, `PhysicalReasoningParameters`), all composed into a
single `PhysicistHeuristics` object. This makes every heuristic a candidate
model that can be tuned per deployment. When a heuristic is replaced by a
learned strategy, its parameter group is deleted — no thresholds, no config.

See [ADR 0003](/docs/adr/0003-physicist-config-driven-heuristics.md) for the
full rationale and migration plan.

---

## Research Question

How should an autonomous cognitive runtime maintain an internal physical representation
of the world that is simultaneously real-time, computationally efficient, uncertainty-aware,
explainable, useful for planning, scheduling, reasoning, and scalable?

---

## The Physicist Cognitive Node

Defined in `src/cores/core/physicist.py`. The Physicist is a `Module` registered with
the Runtime's execution cycle. It continuously executes the following cognitive loop:

```
Observe → Associate observations → Update beliefs → Estimate physical state →
Predict future state → Check physical consistency → Update confidence →
Publish understanding → Repeat
```

### Responsibilities

| Responsibility | Implementation |
|---|---|
| Observation association | Modules write to `context.world_model` (the strategy); Physicist reads after all modules |
| Belief updates | Delegated to the `WorldModelStrategy` (upsert/update) |
| Physical state estimation | Strategy tracks position, velocity, acceleration per object |
| Prediction | Strategy's `predict()` method |
| Uncertainty management | Strategy's confidence and uncertainty state |
| Physical consistency | `_check_consistency()` — detects self-detections, impossible velocities |
| Explanation generation | `_generate_explanation()` — produces human-readable summary |

### Integration

- Runtime creates a `Physicist` in `__init__()`, passing the chosen strategy
- `runtime.context.world_model` is wired to `physicist.strategy` before module execution
- After all modules run, `physicist.execute()` runs the cognitive loop
- `RuntimeStateBuilder` reads from `physicist.strategy` for the world snapshot
- `physicist.last_explanation` is included in `RuntimeState.explainability`

---

## WorldModelStrategy Interface

Defined as an abstract base class in `src/cores/core/world_model/interface.py`:

```python
class WorldModelStrategy(ABC):
    update_environment(**kwargs)       # Ingest environment observations
    upsert_object(...)                  # Create or update tracked object
    get_object(object_id)              # Retrieve single object
    get_objects_by_type(object_type)   # Filter by type
    remove_stale_objects(cycle, age)   # Age-based cleanup
    remove_object(object_id)           # Explicit removal
    predict(steps, **kwargs)           # Predict future state
    serialize()                        # Export for bridge/snapshot
    explain()                          # Human-readable explanation
```

Properties: `environment`, `objects`, `uncertainty`, `obstacle_count`,
`has_sensor_degradation`, `last_update_cycle`

The strategy only answers: "Given observations and current beliefs, how should the
physical understanding be updated?" All cognitive orchestration belongs to the Physicist.

---

## Candidate Reasoning Strategies

### 1. SimpleObjectRegistry (Baseline)

| File | `src/cores/core/world_model/simple_registry.py` |
|-|-|

Stores objects as a flat list with no spatial or kinematic reasoning.

**Strengths**: Fast type queries (18 us), minimal serialization size (19.3 KB/100 objects),
trivial implementation.

**Weaknesses**: No prediction, no spatial indexing, no kinematic tracking.

**Use case**: Baseline for comparison against all other approaches.

---

### 2. OccupancyGrid

| File | `src/cores/core/world_model/occupancy_grid.py` |
|-|-|

Classic robotics occupancy grid with log-odds cell updates.

**Strengths**: Fastest single-object lookup (41 us), spatial region queries,
explicit free/occupied representation.

**Weaknesses**: Memory proportional to grid size, slow explain latency (3500 us),
no temporal prediction.

**Design decisions**:
- Fixed grid with configurable resolution, width, height
- Log-odds update: +0.8 for occupied, -0.4 for free, clamped to [-4, 4]
- Objects tracked in parallel with grid cells (object-aware)

---

### 3. SemanticWorldModel

| File | `src/cores/core/world_model/semantic.py` |
|-|-|

Knowledge-graph representation with typed nodes and edges.

**Strengths**: Fastest update latency (940 us), fast runtime integration (274 us/step),
built-in relation system, explain-friendly structure.

**Weaknesses**: No spatial index, no prediction, relation cleanup on removal is O(E).

**Design decisions**:
- Node types: region, agent, object, obstacle, waypoint, landmark
- Edge relations: located_in, connected_to, etc.
- Default nodes for "environment" and "robot" created at init
- Environment property changes automatically sync to "environment" node

---

### 4. ProbabilisticWorldModel

| File | `src/cores/core/world_model/probabilistic.py` |
|-|-|

Bayesian belief tracking with per-object confidence and variance.

**Strengths**: Uncertainty-aware, confidence increases with repeated observations,
prediction confidence decays over time.

**Weaknesses**: High tracking error (20.2 mean) - Bayesian update with naive
measurement model is unstable with noisy sensors; no spatial index.

**Design decisions**:
- Kalman-gain fusion for each position axis independently
- Measurement variance derived from `1.0 - uncertainty.perception`
- Belief state: mean, variance, confidence, prior_weight

---

### 5. DynamicTrackingWorldModel

| File | `src/cores/core/world_model/dynamic_tracking.py` |
|-|-|

Kalman filter with constant-velocity model and 4x4 covariance matrix.

**Strengths**: Best prediction error (0.163), fast stale removal (27 us),
velocity tracking, motion queries.

**Weaknesses**: Slow update latency (14,430 us), no spatial indexing,
constant-velocity model limited for accelerating objects.

**Design decisions**:
- State vector: [x, y, vx, vy]
- Standard predict-update Kalman cycle
- Velocity decay (0.95) for long-term prediction stability
- Full matrix operations for covariance propagation

---

### 6. SSKPM (Streaming Spatial Kinematic Physics Mapping)

| File | `src/cores/core/world_model/sskpm.py` |
|-|-|

CORES' proposed physical reasoning strategy integrating spatial chunks,
kinematic state (9-DOF), Bayesian fusion, semantic tags, and explainability logging.

**Strengths**: Best tracking accuracy (0.431 mean error), best max tracking error (0.665),
kinematic model (velocity + acceleration), spatial chunk indexing,
region/nearest queries, explainability log, 3D position support.

**Weaknesses**: Highest update latency (66,300 us) due to 9x9 covariance matrix
operations; largest serialized output (33.5 KB).

**Design decisions**:
- **Spatial chunks**: Fixed-size grid tiles (5m default) for O(1) region lookup
- **Kinematic state**: 9-DOF [x, y, z, vx, vy, vz, ax, ay, az] with full 9x9 covariance
- **Streaming update pipeline**: associate -> predict -> update -> cleanup
- **Prediction model**: Constant-acceleration with velocity decay (0.9)
  and acceleration decay (0.8)
- **Explainability**: Append-only log of create/update/stale operations
- **Object identity**: Track IDs persist across cycles; confidence fuses
  observation confidence with temporal decay
- **Semantic tags**: Each track carries a list of semantic tags for
  cross-modal reasoning

---

## Benchmark Results

### Methodology

All 6 strategies evaluated under identical scenarios measuring:

- **Runtime**: update latency, lookup latency, query latency, serialization size
- **Robotics**: tracking error (moving object), prediction error (future position)
- **Utility**: runtime integration cost, stale removal, explain latency

### Summary Table

| Metric | Best Strategy | Value | Runner-Up |
|--------|--------------|-------|-----------|
| Update latency | SemanticWorldModel | 1,625 us | Probabilistic (1,985 us) |
| Lookup latency | OccupancyGrid | 49 us | SimpleObjectRegistry (618 us) |
| Type query latency | SimpleObjectRegistry | 26 us | OccupancyGrid (33 us) |
| Mean tracking error | SSKPM | 0.431 | DynamicTracking (0.460) |
| Mean prediction error | DynamicTracking | 0.163 | SSKPM (0.332) |
| Max tracking error | SSKPM | 0.665 | SimpleObjectRegistry (0.707) |
| Serialized size | SimpleObjectRegistry | 19.3 KB | DynamicTracking (29.2 KB) |
| Runtime integration | SimpleObjectRegistry | 249 us/step | SemanticWorldModel (275 us) |
| Stale removal | SimpleObjectRegistry | 18 us | Probabilistic (33 us) |
| Explain latency | SimpleObjectRegistry | 6 us | SemanticWorldModel (9 us) |

### Key Findings

1. **No single strategy dominates all metrics.** Trade-offs are necessary.

2. **SSKPM wins on tracking accuracy** (mean error 0.431, max error 0.665)
   but has the highest update latency. The full 9x9 covariance matrix
   operations are expensive but provide the best kinematic understanding.

3. **DynamicTrackingWorldModel wins on prediction** (mean error 0.163)
   with a simpler 4x4 Kalman filter optimized for constant-velocity scenarios.

4. **SemanticWorldModel is the fastest at updates** (1,625 us). Its graph
   structure is naturally efficient for the operation patterns in a cognitive runtime.

5. **ProbabilisticWorldModel shows instability** with large position jumps
   (tracking error 20.2). The independent per-axis Bayesian update
   doesn't handle correlated position changes well.

6. **SimpleObjectRegistry remains competitive** on most metrics despite
   its simplicity, making it a strong baseline.

---

## Recommended Default

For the CORES cognitive runtime, **SimpleObjectRegistry** remains the default
for backward compatibility. To use SSKPM (recommended for best accuracy):

```python
runtime = Runtime(scheduler, execution_layer, world_model=SSKPM())
```

SSKPM is recommended because:
1. **Best tracking accuracy** — critical for planning and navigation
2. **Kinematic prediction** — velocity + acceleration model enables future state estimation
3. **Spatial indexing** — chunks enable efficient region queries
4. **Explainable** — operation log enables the Scientist node to audit understanding
5. **3D position support** — essential for aerial or underwater operations

If latency becomes a bottleneck, **SemanticWorldModel** provides the
best update performance and is the recommended fallback.

All strategies are interchangeable via the `WorldModelStrategy` ABC,
so the Runtime can switch between them without any code changes.

---

## File Map

| File | Role |
|---|---|
| `src/cores/core/physicist.py` | Physicist cognitive module |
| `src/cores/core/world_model/interface.py` | `WorldModelStrategy` ABC + `WorldModel` alias |
| `src/cores/core/world_model/types.py` | Shared data types |
| `src/cores/core/world_model/simple_registry.py` | Baseline strategy |
| `src/cores/core/world_model/occupancy_grid.py` | Grid-based strategy |
| `src/cores/core/world_model/semantic.py` | Knowledge-graph strategy |
| `src/cores/core/world_model/probabilistic.py` | Bayesian strategy |
| `src/cores/core/world_model/dynamic_tracking.py` | Kalman filter strategy |
| `src/cores/core/world_model/sskpm.py` | CORES proposed strategy |
| `tests/test_physicist.py` | Physicist unit tests (24) |
| `tests/test_world_model.py` | Strategy unit tests (21) |
| `tests/test_world_model_implementations.py` | Cross-strategy tests (138) |
| `tests/benchmark_world_models.py` | Strategy benchmark framework |

---

## Future Work

- Profile and optimize SSKPM's 9x9 matrix operations
- Implement hierarchical spatial chunks (quadtree-like)
- Add object association across cycles (appearance matching)
- Benchmark with real sensor data (LiDAR, camera, IMU)
- Evaluate impact on Planner, Traveller, and Scientist node quality
- Explore hybrid model: SSKPM for tracking + Semantic for reasoning
- Add Particle Filter as an additional strategy
- Implement the Physicist's observation ingestion via EventBus
- **Replace heuristics with learned strategies**: association distance,
  physical reasoning rules, confidence dynamics — all currently configurable
  via `PhysicistConfig` — should eventually be inferred from evidence
  (Bayesian programme induction, online parameter optimisation, etc.)
