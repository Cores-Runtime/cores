# Phase 4G: Memory Subsystem -- Research and Strategy Comparison

## Approaches Studied

### Working Memory

Stores only the current cycle's relevant information. Capacity-limited (7+-2 items).
Rapid access, high churn.
Good for: keeping the current plan context available.
Bad for: long-term recall, learning from past failures.

### Episodic Memory

Stores sequences of events as episodes. Each episode has a start, an end, and a context.
Good for: remembering "what happened last time we tried this approach."
Bad for: defining episode boundaries is heuristic. Wrong boundaries produce wrong recall.

### Semantic Memory

Stores facts and concepts independent of when they were learned.
Good for: "rocks are hard to traverse," "the GPS was unreliable at the north ridge."
Bad for: recalling specific past events. Requires a separate consolidation process.

### Event-Based Memory

Stores discrete events with timestamps and type tags.
Good for: "we saw an obstacle at (x,y) 40 cycles ago."
Bad for: inferring patterns across events. Needs query mechanisms.

### Blackboard Systems

A shared data structure where modules read and write information.
Good for: multiple modules contributing and consuming data.
Bad for: contention, stale data, lack of ownership.

### Memory Consolidation

The process of converting short-term experiences into long-term storage.
Rehearsal, importance weighting, sleep-like offline processing.
Good for: keeping what matters, dropping what does not.
Bad for: computational cost. Full consolidation is expensive.

### SPSCA (Semantic Pointer State Compression Algorithm)

Uses fixed-size vector signatures (semantic pointers) to compress state.
Records are addressable by content similarity, not just by key.
Good for: fixed memory footprint, similarity-based retrieval.
Bad for: requires a good compression function. Hash collisions lose information.

## Strategy Comparison

| Approach | Retrieval | Forgetting | Cost | Use Case |
|---|---|---|---|---|
| FIFO | O(n) scan | O(1) drop oldest | Low | Bounded queue, recent events only |
| TimeDecay | O(n) scan | O(n) prune expired | Medium | Time-sensitive recall |
| Priority | O(n) scan | O(n) prune low | Medium | Important info must survive |
| Episodic | O(n) scan | O(n) prune old episodes | Medium | Sequence-aware recall |
| SPSCA | O(n) similarity | O(n) prune low-similarity | Medium | Content-addressable recall |

## Recommendation

Use Priority memory with importance decay as the default strategy. It balances bounded memory growth against useful information survival. Episodic and SPSCA are useful for specific Planner queries (sequence recall and similarity matching respectively). FIFO is the simplest baseline for benchmarks.

SPSCA is the right direction for long-term cognitive architecture, but the current codebase does not have a vector embedding system. The SPSCA implementation uses content hashing as a practical substitute. True semantic pointers would require a neural network or learned encoder.

## Next Steps

1. Implement the interface and all five strategies.
2. Benchmark each strategy on retrieval latency, memory growth, and forgetting behavior.
3. Integrate into the Runtime pipeline.
4. Update the Planner to query memory through PlanningContext.
