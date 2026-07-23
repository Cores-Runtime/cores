"""Demonstrate SPSCA memory with the hospital delivery scenario.

Simulates multiple runtime cycles:
  StateEstimation -> Memory -> Planner -> Execution -> Memory (feedback)

Run:  uv run python demo_memory.py
"""

import sys
sys.path.insert(0, "src")

from cores.core.memory import (
    MemoryRecord,
    MemoryQuery,
    SPSCAMemoryStrategy,
)
from cores.core.memory.semantic_pointers import SemanticPointer, encode_content


def heading(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def main() -> None:
    # similarity_threshold=0.0 means we rely on metadata filters (type, importance),
    # not vector similarity.  This is intentional: the current SHA256-based encoding
    # maps each string to a unique random vector, so partial-text matching doesn't work.
    # A future learned encoder would enable true semantic similarity.
    memory = SPSCAMemoryStrategy(
        max_size=1000,
        max_individual=10,
        similarity_threshold=0.0,
        dim=512,
    )

    # =====================================================================
    # Cycle 1: Robot sees Room 12, door closed
    # =====================================================================
    heading("CYCLE 1: Observation")

    print("  StateEstimation:")
    observation = {"room": "Room 12", "door": "closed", "battery": 80}
    print(f"    Sensors see: {observation}")

    print("  Memory: store observation")
    memory.store(MemoryRecord(
        id=f"obs_{1}",
        content=observation,
        cycle=1,
        importance=0.6,
        record_type="observation",
    ))
    print(f"    Stored.  Memory size: {memory.size}")

    print("  Planner decides: OpenDoor")
    plan = "OpenDoor"

    print("  Execution:")
    outcome_text = "Failed"
    print(f"    Action: {plan} -> {outcome_text}")

    print("  Memory: store outcome")
    memory.store(MemoryRecord(
        id=f"outcome_{1}",
        content={"action": "OpenDoor", "target": "Room 12", "result": "Failed"},
        cycle=1,
        importance=0.9,
        record_type="outcome",
    ))
    print(f"    Stored.  Memory size: {memory.size}")

    # =====================================================================
    # Cycle 3: Planner checks memory before retrying
    # =====================================================================
    heading("CYCLE 3: Planner queries memory before retrying")

    print("\n  Planner asks: \"Has OpenDoor failed on Room 12?\"")
    print("  Memory: retrieve outcomes with min_importance=0.5")
    result = memory.retrieve(MemoryQuery(
        query="",
        record_types=["outcome"],
        min_importance=0.5,
        limit=5,
    ))

    if result.records:
        print(f"    Found {len(result.records)} matching outcome(s):")
        for r in result.records:
            c = r.content
            print(f"      [{r.record_type}] action={c['action']} target={c['target']} result={c['result']}")
        print("\n    -> Memory says: yes, OpenDoor failed on Room 12.")
        print("    -> Planner: try another entrance.")
    else:
        print("    No matching outcomes found.")

    # =====================================================================
    # Cycles 4-8: Accumulate more experiences
    # =====================================================================
    heading("CYCLES 4-8: Accumulating experiences")

    experiences = [
        ("observation", {"room": "Corridor B", "obstacle": "human", "count": 3}),
        ("outcome", {"action": "Navigate", "route": "Corridor B", "result": "Success"}),
        ("observation", {"room": "Charging Station", "status": "available"}),
        ("outcome", {"action": "Charge", "result": "Success", "gain": 20}),
        ("observation", {"room": "Room 12", "door": "still closed", "battery": 60}),
    ]
    for i, (rtype, content) in enumerate(experiences, start=4):
        memory.store(MemoryRecord(
            id=f"rec_{i}",
            content=content,
            cycle=i,
            importance=0.5 + i * 0.05,
            record_type=rtype,
        ))
    print(f"  Stored 5 more records.  Memory size: {memory.size}")

    # =====================================================================
    # Query by record_type only
    # =====================================================================
    heading("FILTERED QUERY: All observations")

    result = memory.retrieve(MemoryQuery(
        query="",
        record_types=["observation"],
        min_importance=0.0,
        limit=10,
    ))
    print(f"  Found {len(result.records)} observations:")
    for r in result.records:
        print(f"    [cycle {r.cycle}] {r.content}")

    # =====================================================================
    # Chunking: low-importance records compress into chunks
    # =====================================================================
    heading("CHUNKING: Compression via superposition")

    print(f"  max_individual=10, records before bulk: {memory.size}")
    for i in range(10):
        memory.store(MemoryRecord(
            id=f"noise_{i}",
            content={"sensor_noise": i, "value": 0.1},
            cycle=30 + i,
            importance=0.05 + i * 0.01,
            record_type="noise",
        ))
    print(f"  After 10 noise records: {memory.size} individual + {memory.chunk_count} chunk(s)")
    print(f"  Total stored (individual + chunks): {memory.total_stored}")

    # =====================================================================
    # Semantic pointer algebra
    # =====================================================================
    heading("SEMANTIC POINTER ALGEBRA")

    robot_sp = encode_content("Robot", dim=128)
    picked_sp = encode_content("picked", dim=128)
    medicine_sp = encode_content("Medicine", dim=128)

    # Encode: Robot (r) picked (p) Medicine (m) via binding: r ⊗ p ⊗ m
    fact_sp = robot_sp.bind(picked_sp).bind(medicine_sp)
    print(f"\n  Bound vector (r x p x m): {fact_sp.dimension}D")

    # Unbind to recover: (r x p x m) .unbind(m) .unbind(p) ~= r
    recovered_who = fact_sp.unbind(medicine_sp).unbind(picked_sp)
    sim = robot_sp.similarity(recovered_who)
    print(f"  Unbind 'Medicine' then 'picked' -> recover 'Robot': sim = {sim:.3f}")

    # Unbind to recover action: (r x p x m) .unbind(m) .unbind(r) ~= p
    recovered_what = fact_sp.unbind(medicine_sp).unbind(robot_sp)
    sim = picked_sp.similarity(recovered_what)
    print(f"  Unbind 'Medicine' then 'Robot' -> recover 'picked': sim = {sim:.3f}")

    # =====================================================================
    # Summary
    # =====================================================================
    heading("SUMMARY")
    m = memory.metrics
    print(f"  Records stored:        {m.insertion_count}")
    print(f"  Queries answered:      {m.retrieval_count}")
    print(f"  Current individual:    {memory.size}")
    print(f"  Compressed chunks:     {memory.chunk_count}")
    print()
    print("  What works now:")
    print("    - Store observations (from StateEstimation)")
    print("    - Store outcomes (from Execution feedback)")
    print("    - Query by record_type + min_importance filters")
    print("    - Low-importance records compress into superposed chunks")
    print("    - Semantic pointer bind/unbind for structured knowledge")
    print()
    print("  What needs a learned encoder for true semantic search:")
    print("    - 'Has this plan failed before?' (partial-text matching)")
    print("    - 'Which route usually succeeds?' (cross-record inference)")
    print("    - Fuzzy similarity across different phrasings")


if __name__ == "__main__":
    main()
