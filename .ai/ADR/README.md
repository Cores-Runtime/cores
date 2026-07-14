# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the CORES Runtime.

An ADR documents a significant architectural decision — what was decided, why, and what consequences it carries. ADRs are immutable once accepted. Superseded decisions get a new ADR that references the old one.

## Format

Each ADR follows this structure:

```
# ADR-XXXX: Title

Date: YYYY-MM-DD
Status: Proposed | Accepted | Superseded | Deprecated

## Context
Why did this decision need to be made?

## Decision
What was decided?

## Consequences
What are the positive and negative outcomes?
```

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-runtime-orchestrator.md) | Runtime as Pure Orchestrator | Accepted |
| [0002](0002-stateless-eventbus.md) | Stateless EventBus | Accepted |
| [0003](0003-immutable-events.md) | Immutable Events with Frozen Pydantic Models | Accepted |
| [0004](0004-event-type-strenum.md) | EventType as StrEnum | Accepted |
| [0005](0005-scheduling-policy.md) | SchedulingPolicy as Separate Abstraction | Accepted |
| [0006](0006-module-result.md) | ModuleResult as a Stable Boundary Interface | Accepted |
| [0007](0007-synchronous-execution.md) | Synchronous Execution in Phase 1 | Accepted |
