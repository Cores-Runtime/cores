# Memory: "What happened, and what does it mean?"

The Memory cognitive node answers two questions:

1. **Episodic**: "what happened?" Raw observations, actions, plans, and outcomes.
2. **Semantic**: "what tends to happen when we do X?" Compressed narratives distilled from experience.

It sits between StateEstimation and Planning. StateEstimation writes observations into memory. The Planner reads memory before proposing plans. Execution feedback (outcomes) is written back into memory, so the robot gets better over time.

## Structure

```
Memory
├── EpisodicStore     raw records, one MemoryStrategy underneath
├── Logger            compresses archived records into narratives
└── SemanticStore     narratives + facts + confidence
```

- **EpisodicStore** wraps a `MemoryStrategy` (FIFO, Priority, TimeDecay, Episodic) that decides storage, eviction, and forgetting. Records move through a lifecycle: `NEW -> ACTIVE -> ARCHIVED -> CONSOLIDATED -> DISCARDED`.
- **Logger** reads ARCHIVED records, compresses them with SPSCA (Semantic Pointer State Compression), and stores the result in SemanticStore. It does not run every cycle; a `TriggerPolicy` decides when.
- **SemanticStore** is a simple dict-backed store for `NarrativeRecord`s, facts, and confidence values. No interchangeable strategies needed.

## Usage

```python
from cores.core import Memory, MemoryRecord, MemoryQuery, MemoryType

memory = Memory()  # defaults: PriorityMemoryStrategy + SPSCALogger

memory.store(MemoryRecord(
    id="outcome_1",
    content={"action": "OpenDoor", "result": "Failed"},
    cycle=1,
    importance=0.9,
    record_type=MemoryType.OUTCOME,
))
memory.execute(state, context)

result = memory.query(MemoryQuery(
    memory_types=[MemoryType.OUTCOME],
    max_results=5,
))
```

`Memory.query()` merges episodic and semantic results, so planners never choose which store to query. They just ask.

### For planners: `Memory.evidence()`

Planners consume *evidence*, not raw records. `Memory.evidence(query=None)` aggregates
stored OUTCOME records (matching `query.action` / `query.location` when given) and
NARRATIVE records into an `EvidenceSet`:

- `failure_count(action)` / `success_count(action)`: how many times an action failed / succeeded
- `narratives`: `NarrativeEvidence(topic, confidence, count)`

`MemoryAwarePlanner` reads this before planning and biases candidate scores through a
`MemoryInfluencePolicy`. Because memory owns the record format, planners stay decoupled
from how records are stored. See `tests/test_memory_evidence.py`.

### Customising

```python
from cores.core import Memory, EpisodicStore, FIFOMemoryStrategy

memory = Memory(
    episodic_store=EpisodicStore(FIFOMemoryStrategy(max_size=500)),
    semantic_store=SemanticStore(),
    logger=Logger(SPSCALogger(), trigger=CountTrigger(count=20)),
    archive_below=0.6,  # records below this importance get ARCHIVED for the Logger
)
```

If you pass nothing, `Memory()` builds sensible defaults internally. During each `execute()`
cycle, records below `archive_below` (default 0.3) transition ACTIVE to ARCHIVED, and the
Logger consolidates them into narratives when its trigger fires.

## Record types

`MemoryType`: `OBSERVATION`, `ACTION`, `PLAN`, `OUTCOME`, `EPISODE`, `SEMANTIC`, `NARRATIVE`.

## Query fields

`MemoryQuery`: `memory_types`, `location`, `action`, `topic`, `lifecycle`, `query_text`, `min_importance`, `max_age_cycles`, `max_results`.

## Files

| File | What's in it |
|---|---|
| `src/cores/core/memory/types.py` | MemoryType, RecordLifecycle, MemoryQuery, NarrativeRecord, CompressionMetadata |
| `src/cores/core/memory/interface.py` | MemoryRecord, MemoryResult, MemoryMetrics, MemoryStrategy, Memory |
| `src/cores/core/memory/store.py` | EpisodicStore, SemanticStore |
| `src/cores/core/memory/strategies/` | FIFO, Priority, TimeDecay, Episodic strategies |
| `src/cores/core/logger/` | Logger, SPSCALogger, trigger policies |
| `tests/test_memory.py` | Memory + strategy tests |
| `tests/test_logger.py` | Logger pipeline integration tests |
| `tests/test_spsca.py` | SPSCA algorithm tests |
| `tests/test_trigger_policy.py` | Trigger policy tests |
| `demo_memory.py`, `demo_logger.py` | Run the pipeline end to end |
