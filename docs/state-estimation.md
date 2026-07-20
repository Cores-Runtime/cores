# StateEstimation - Cognitive Node for Physical Understanding

Part of Phase 4B. The StateEstimation cognitive node continuously executes a 10-step cognitive loop: Observe → Associate → Fuse → Update → Predict → Reason → Check Consistency → Manage Confidence → Explain → Publish.

```
StateEstimation
├── ObservationAssociation    - match sensor observations to tracked objects via spatial proximity
├── SensorFusion              - confidence-weighted multi-sensor fusion
├── PhysicalReasoning         - causal motion classification (stationary, constant velocity, external force, gravity)
├── ConsistencyChecker        - detect self-detections, impossible speeds, overlaps, temporal anomalies
├── ConfidenceManager         - decay/boost belief confidence over time
├── Explainability Engine     - human-readable understanding summary
└── WorldModelStrategy        - 6 pluggable physical reasoning backends
```

## World Model Strategies

| Strategy | File | Specialty |
|---|---|---|
| **SimpleObjectRegistry** | `simple_registry.py` | Baseline - flat list, no spatial/kinematic reasoning |
| **OccupancyGrid** | `occupancy_grid.py` | Classic log-odds grid with free/occupied cells |
| **SemanticWorldModel** | `semantic.py` | Knowledge graph with typed nodes and relations |
| **ProbabilisticWorldModel** | `probabilistic.py` | Bayesian belief tracking with per-object variance |
| **DynamicTrackingWorldModel** | `dynamic_tracking.py` | Kalman filter (4x4 covariance, constant-velocity) |
| **SSKPM** | `sskpm.py` | 9-DOF kinematic + spatial chunk indexing + Bayesian fusion |

## Benchmark Results

| Metric | Best | Value | Runner-Up |
|---|---|---|---|
| Update latency | SemanticWorldModel | 1,625 µs | Probabilistic (1,985 µs) |
| Lookup latency | OccupancyGrid | 49 µs | SimpleObjectRegistry (618 µs) |
| Tracking accuracy | **SSKPM** | **0.431 mean error** | DynamicTracking (0.460) |
| Prediction error | DynamicTracking | **0.163** | SSKPM (0.332) |
| Serialized size | SimpleObjectRegistry | 19.3 KB | DynamicTracking (29.2 KB) |
| Runtime integration | SimpleObjectRegistry | 249 µs/step | SemanticWorldModel (275 µs) |

Default strategy is `SimpleObjectRegistry`. Switch to `SSKPM` for best accuracy:

```python
runtime = Runtime(scheduler, execution_layer, world_model=SSKPM())
```

## Heuristic Parameters

All heuristic thresholds are configurable via `StateEstimationHeuristics`, separated from runtime options (`StateEstimationConfig`). Each sub-component has its own parameter dataclass (e.g. `AssociationParameters`, `PhysicalReasoningParameters`). When a heuristic is replaced by a learned model, its parameter group is deleted entirely.

## Source

- `src/cores/core/state_estimation.py` - cognitive node
- `src/cores/core/world_model/` - all strategy implementations
- `tests/test_state_estimation.py` - 72 tests
- `tests/test_world_model_implementations.py` - 138 cross-strategy tests
- `tests/benchmark_world_models.py` - benchmark framework
