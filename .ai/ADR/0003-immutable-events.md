# ADR-0003: Immutable Events with Frozen Pydantic Models

**Date**: 2026-07-15
**Status**: Accepted

## Context

Events are published to the `EventBus` and dispatched to potentially multiple subscribers. If a subscriber could mutate the event object, subsequent subscribers would observe a different state, breaking determinism.

## Decision

`Event` is a Pydantic model with `frozen=True`. All fields are set at construction and cannot be mutated afterward.

Every event contains exactly:
- `event_type: EventType` — the routing key
- `source: str` — the originating component name
- `timestamp: datetime` — auto-assigned at creation
- `payload: Dict[str, Any]` — optional arbitrary data

No additional fields unless a concrete requirement demands them.

## Consequences

- **Positive**: Deterministic event processing — all subscribers observe the same object.
- **Positive**: Events are safe to pass across component boundaries without defensive copying.
- **Positive**: Mutation bugs are caught at runtime as `ValidationError` / `TypeError`.
- **Negative**: Payload contents remain mutable (dict values). Callers must not mutate nested payload objects.
- **Constraint**: `Event` must never gain mutable fields without revisiting this ADR.
