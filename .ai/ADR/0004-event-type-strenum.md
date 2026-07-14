# ADR-0004: EventType as StrEnum

**Date**: 2026-07-15
**Status**: Accepted

## Context

Events need a routing key so that `EventBus` can dispatch them to the correct subscribers. The naive approach is raw strings (e.g., `"diagnostic"`, `"state_updated"`). Raw strings are typo-prone, unsupported by IDE autocompletion, and fragile to rename refactors.

## Decision

All event types are defined as a centralized `EventType(StrEnum)` in `cores/events/event_type.py`. `StrEnum` was chosen over plain `Enum` because:

1. Values serialize directly to their string representation — no `.value` unwrapping needed.
2. Subscribers and publishers use the same enum constant, enabling IDE navigation and static analysis.
3. String equality is preserved, so `EventType.DIAGNOSTIC == "DIAGNOSTIC"` is true, maintaining compatibility with serialized payloads.

## Consequences

- **Positive**: Typos in event type names are caught at import time.
- **Positive**: All valid event types are discoverable from one file.
- **Positive**: Renaming an event type is a single-point refactor.
- **Negative**: Adding a new event type requires editing `event_type.py` — there is no dynamic registration.
- **Constraint**: Raw strings must never be used as event routing keys anywhere in the codebase.
