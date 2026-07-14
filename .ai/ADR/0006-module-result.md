# ADR-0006: ModuleResult as a Stable Boundary Interface

**Date**: 2026-07-15
**Status**: Accepted

## Context

`Module.execute()` needs to return something to the runtime. The minimal approach is a boolean success flag or a void return. However, `ModuleResult` is the natural boundary between the cognitive layer and the runtime infrastructure — the one interface that is certain to remain stable while everything else evolves. Designing it poorly now means breaking API changes later.

## Decision

`ModuleResult` is a Pydantic model designed as a permanent, stable interface boundary. It contains:

| Field | Type | Purpose |
|---|---|---|
| `module_name` | `str` | Identifies the producing module |
| `status` | `ModuleStatus` | Explicit outcome: `SUCCESS`, `FAILURE`, `SKIPPED` |
| `events` | `List[Event]` | Events to be published this cycle |
| `metrics` | `Dict[str, Any]` | Execution telemetry (latency, output counts, etc.) |
| `execution_time_ms` | `float` | Wall-clock execution duration |
| `error_message` | `Optional[str]` | Failure detail; `None` on success |

`ModuleStatus` is a `StrEnum` — explicit, serializable, and extensible.

The deprecated `success: bool` field was removed in favor of `ModuleStatus` to enable the `SKIPPED` state and remove ambiguity.

## Consequences

- **Positive**: `ModuleResult` can carry telemetry, events, and status in a single typed object.
- **Positive**: `metrics` allows profiling data to flow from modules to the runtime without coupling.
- **Positive**: `error_message` enables structured error handling without exceptions crossing the boundary.
- **Positive**: `ModuleStatus.SKIPPED` allows policies to differentiate intentional no-ops from failures.
- **Negative**: More fields than strictly needed for Phase 1 — `metrics` and `execution_time_ms` are not yet consumed.
- **Rationale for early design**: This interface will outlast Phase 1. The cost of redesigning it later (breaking all modules) is higher than the cost of including unused fields now.
- **Constraint**: `ExecutionLayer` returns `List[ModuleResult]` to `Runtime`. It must never publish events itself.
