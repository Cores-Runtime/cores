# Logger: Consolidation, not narration

The Logger is the consolidation engine inside Memory. It turns raw episodic records into
compressed semantic narratives, so the runtime can answer "what tends to happen when we do X?"
instead of only "what happened?"

It is a class inside the Memory node, not a separate runtime Module. Memory calls it during
`execute()` when a trigger condition is met.

## Why not every cycle?

Learning is a behavior, not a destination. Running consolidation every cycle wastes compute.
The Logger runs only when a `TriggerPolicy` says so:

- **CapacityTrigger**: fires when the episodic store exceeds a size threshold
- **CountTrigger**: fires after N new records since the last run
- **IdleTrigger**: fires when the robot has been idle for M cycles
- **CompositeTrigger**: combine several triggers with AND/OR logic

## How a consolidation pass works

1. Read ARCHIVED records from EpisodicStore.
2. Compress them with a `LoggerStrategy` (SPSCA by default).
3. Write the resulting narratives to SemanticStore.
4. Mark the source records CONSOLIDATED.

## SPSCA

SPSCA (Semantic Pointer State Compression) encodes each record as a high-dimensional vector,
then superposes records of the same type into a single chunk. A chunk preserves approximate
semantic content without keeping every raw record. Each narrative carries provenance
metadata: which source records produced it, their importance statistics, the compression
method, and when it ran. That metadata supports explainability, debugging, replay, and
citing back to episodic memory.

## Usage

```python
from cores.core import Logger, SPSCALogger, CountTrigger

logger = Logger(
    strategy=SPSCALogger(),
    trigger=CountTrigger(count=20),
)
```

Or rely on the default inside `Memory()`:

```python
from cores.core import Memory

memory = Memory()  # Logger with SPSCALogger + CountTrigger(50) wired in
```

## Files

| File | What's in it |
|---|---|
| `src/cores/core/logger/interface.py` | LoggerStrategy ABC |
| `src/cores/core/logger/spsca.py` | SPSCALogger |
| `src/cores/core/logger/triggers.py` | CapacityTrigger, CountTrigger, IdleTrigger, CompositeTrigger |
| `src/cores/core/logger/logger.py` | Logger orchestrator |
| `tests/test_logger.py` | Integration tests |
| `tests/test_spsca.py` | SPSCA algorithm tests |
| `tests/test_trigger_policy.py` | Trigger tests |
| `benchmarks/logger_benchmarks.py` | Compression latency + confidence |
