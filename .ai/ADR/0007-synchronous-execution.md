# ADR-0007: Synchronous Execution in Phase 1

**Date**: 2026-07-15
**Status**: Accepted

## Context

A cognitive runtime could be designed with async coroutines, thread pools, or concurrent module execution to maximize throughput. However, at this stage the runtime has not been benchmarked. No measured deficiency in single-threaded execution exists. Introducing concurrency without evidence of necessity would add correctness complexity before the foundation is proven.

## Decision

All execution in Phase 1 is synchronous. `Module.execute()` is a plain synchronous method. The `Runtime.step()` cycle is sequential. No `asyncio`, thread pools, queues, or locks are used.

Concurrency may be introduced in a future phase only after:
1. Benchmarks demonstrate that sequential execution is a measured bottleneck.
2. The synchronous foundation has been validated as correct under integration tests.

## Consequences

- **Positive**: The runtime is deterministic — cycle output is fully reproducible given identical inputs.
- **Positive**: Debugging is straightforward — no race conditions, no deadlocks, no event loop overhead.
- **Positive**: Unit tests are simple — no async test infrastructure required.
- **Negative**: All modules share the same thread. A slow module blocks the entire cycle.
- **Negative**: Cannot exploit multiple cores in Phase 1.
- **Constraint**: `async def execute()` must not appear in any `Module` implementation. If async I/O is needed, wrap it in a synchronous boundary.
