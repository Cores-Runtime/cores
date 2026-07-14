# ADR-0001: Runtime as Pure Orchestrator

**Date**: 2026-07-15
**Status**: Accepted

## Context

The runtime system needed a central coordinator to own all components (`RobotState`, `RuntimeContext`, `EventBus`, `Scheduler`, `ExecutionLayer`) and drive the execution cycle. An early design risked collapsing scheduling logic, module invocation, and event routing into a single class.

## Decision

`Runtime` is a pure orchestrator. It owns components, coordinates the lifecycle of one execution cycle, and passes data between components. It contains no scheduling heuristics, no module logic, and no cognitive planning.

One cycle is strictly sequential:

```
Collect Events → Scheduler → ExecutionPlan → ExecutionLayer → Publish Events → Advance Context
```

## Consequences

- **Positive**: Each component is independently testable. Runtime can be swapped without touching Scheduler or ExecutionLayer.
- **Positive**: Cycle flow is auditable by reading a single `step()` method.
- **Negative**: Runtime must be updated if the cycle sequence ever changes.
- **Constraint**: Runtime must never invoke `module.execute()` directly.
