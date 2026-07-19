# ADR 0003: Physicist — Separating Heuristic Parameters from Runtime Config

**Status:** Accepted
**Date:** 2026-07-19
**Author:** CORES Architecture Team

---

## Context

The Physicist cognitive node (Phase 4B) relies on several heuristic thresholds to
implement its cognitive loop: observation association distance, sensor fusion
confidence boost, physical reasoning rules (stationary/acceleration/gravity
detection), consistency checking tolerances, and confidence decay/boost rates.

These were initially hardcoded inside each sub-component, then briefly consolidated
into a single flat `PhysicistConfig` dataclass. That was an improvement, but it
conflated two fundamentally different concepts:

1. **Heuristic parameters** — temporary thresholds that should eventually be
   replaced by learned/adaptive strategies (association distance, gravity
   detection rules, etc.)
2. **Runtime config** — permanent structural options that control *how* the
   Physicist operates (logging, debug mode, sensor config, etc.)

---

## Decision

We split into two separate concepts:

### `PhysicistHeuristics` — composed of sub-component parameter groups

```python
@dataclass
class PhysicistHeuristics:
    association: AssociationParameters       # ObservationAssociation
    fusion: FusionParameters                 # SensorFusion
    reasoning: PhysicalReasoningParameters   # PhysicalReasoning
    consistency: ConsistencyParameters       # ConsistencyChecker
    confidence: ConfidenceParameters         # ConfidenceManager
```

Each sub-component accepts its own parameter group:

```python
class ObservationAssociation:
    def __init__(self, params: Optional[AssociationParameters] = None): ...
```

This makes the migration path explicit: when `ObservationAssociation` is
replaced by a learned association model, `AssociationParameters` disappears
entirely — there's no threshold config, just `model.predict(obs, tracks)`.

### `PhysicistConfig` — runtime options only

```python
@dataclass
class PhysicistConfig:
    # Placeholder — runtime options added as the Physicist evolves.
    pass
```

This stays lean and is *not* a candidate for learned replacement.

### `Physicist` accepts both

```python
Physicist(
    strategy=SSKPM(),
    heuristics=PhysicistHeuristics(...),  # candidate model tuning
    config=PhysicistConfig(...),          # runtime options
)
```

---

## Consequences

### Positive

- **Clear semantic separation** — heuristics are temporary crutches; config is
  permanent structure.
- **Per-sub-component granularity** — each parameter group can be evolved
  independently. When `AssociationParameters` is replaced by a learned model,
  only `ObservationAssociation` changes.
- **Scales to 40+ parameters** — nested structure prevents a flat namespace
  explosion.
- **Backward compatible** — all parameter defaults match the previous hardcoded
  values, so 412+ existing tests pass unchanged.

### Negative

- **More dataclasses** — 7 dataclasses instead of 1. The nesting adds a small
  indirection cost for callers who want to override a single threshold.

---

## Migration

| Before | After |
|--------|-------|
| `PhysicistConfig(association_distance=3.0)` | `PhysicistHeuristics(association=AssociationParameters(distance=3.0))` |
| `ConfidenceManager(PhysicistConfig(decay=0.02))` | `ConfidenceManager(ConfidenceParameters(decay_per_cycle=0.02))` |
| `Physicist(strategy=s, config=cfg)` | `Physicist(strategy=s, heuristics=h, config=c)` |

---

## Future Outlook

Each parameter group's docstring explicitly names its planned replacement:

| Parameter group | Future replacement |
|----------------|--------------------|
| `AssociationParameters` | `association_model.predict(obs, tracks) → probability` |
| `FusionParameters` | Learned per-sensor fusion weights |
| `PhysicalReasoningParameters` | `motion_classifier.predict(vx, vy, ax, ay, ...) → cause` |
| `ConsistencyParameters` | `anomaly_detector.predict(state) → List[Issue]` |
| `ConfidenceParameters` | Adaptive confidence via online parameter estimation |

When any of these replacements lands, its parameter group is deleted — not
deprecated, not defaulted — deleted. No thresholds, no config.
