# ADR-0005: SchedulingPolicy as Separate Abstraction

**Date**: 2026-07-15
**Status**: Accepted

## Context

The `Scheduler` must decide which modules execute each cycle. The decision logic could have been embedded directly inside the `Scheduler` class. However, different runtime modes (default, low-power, emergency) require different selection strategies. Embedding multiple strategies inside `Scheduler` would violate SRP and make future strategy swaps require modifying the coordinator itself.

## Decision

Scheduling logic is extracted into a `SchedulingPolicy` abstract base class. The `Scheduler` is a thin coordinator that delegates entirely to its configured policy:

```python
class Scheduler:
    def schedule(self, modules, state, context, events) -> ExecutionPlan:
        return self.policy.schedule(modules, state, context, events)
```

Phase 1 implements only `DefaultSchedulingPolicy`, which schedules all registered modules in registration order.

`LowPowerPolicy` and `EmergencyPolicy` are explicitly deferred until benchmarks or operational data justify their need.

## Consequences

- **Positive**: New scheduling strategies can be added without touching `Scheduler`.
- **Positive**: Policies are independently unit-testable with identical inputs/outputs.
- **Positive**: `Scheduler` remains a near-pure function coordinator.
- **Negative**: One extra indirection layer for simple default scheduling.
- **Constraint**: `Scheduler` must never contain scheduling heuristics directly. All logic lives in policies.
