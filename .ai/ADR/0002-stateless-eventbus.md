# ADR-0002: Stateless EventBus

**Date**: 2026-07-15
**Status**: Accepted

## Context

The initial `EventBus` prototype stored event history internally. The question arose: should the `EventBus` remember events, or should another component (e.g., a future Narrator/debugger) own that responsibility?

## Decision

`EventBus` is completely stateless. Its only responsibilities are:

- `subscribe(event_type, callback)`
- `unsubscribe(event_type, callback)`
- `publish(event)`

It stores no history, performs no logging, and has zero knowledge of `Scheduler`, `Runtime`, `Modules`, or any other component.

The `Runtime` buffers events by subscribing to all event types at initialization. This buffer is flushed at the start of each cycle and passed to the `Scheduler`.

## Consequences

- **Positive**: `EventBus` is trivially testable and provably correct.
- **Positive**: Memory usage is bounded — no unbounded history accumulation.
- **Positive**: History, replay, and debugging concerns can be added as a separate Narrator component without touching `EventBus`.
- **Negative**: Callers cannot query past events from `EventBus`. They must maintain their own state.
- **Constraint**: `EventBus` must never gain knowledge of any other runtime component.
