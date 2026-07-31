"""Demonstrate memory with the hospital delivery scenario.

Simulates multiple runtime cycles:
  StateEstimation -> Memory -> Planner -> Execution -> Memory (feedback)

Uses the Memory cognitive node (EpisodicStore + SemanticStore + Logger).

Run:  uv run python demo_memory.py
"""

import sys
sys.path.insert(0, "src")

from cores.core.memory import (
    Memory,
    MemoryRecord,
    MemoryQuery,
    MemoryType,
    EpisodicStore,
    FIFOMemoryStrategy,
)
from cores.core.logger import Logger, SPSCALogger, CountTrigger
from cores.core.memory.semantic_pointers import encode_content
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


def heading(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def main() -> None:
    # Memory defaults to PriorityMemoryStrategy + Logger (SPSCA + CountTrigger).
    # Pass explicit stores to customise: Memory(episodic_store=..., semantic_store=..., logger=...).
    memory = Memory()

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
        record_type=MemoryType.OBSERVATION,
    ))
    memory.execute(RobotState(), RuntimeContext())
    print(f"    Stored.  Memory size: {memory.episodic.size}")

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
        record_type=MemoryType.OUTCOME,
    ))
    memory.execute(RobotState(), RuntimeContext())
    print(f"    Stored.  Memory size: {memory.episodic.size}")

    # =====================================================================
    # Cycle 3: Planner checks memory before retrying
    # =====================================================================
    heading("CYCLE 3: Planner queries memory before retrying")

    print("\n  Planner asks: \"Has OpenDoor failed on Room 12?\"")
    print("  Memory: retrieve outcomes with min_importance=0.5")
    result = memory.query(MemoryQuery(
        memory_types=[MemoryType.OUTCOME],
        min_importance=0.5,
        max_results=5,
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
        (MemoryType.OBSERVATION, {"room": "Corridor B", "obstacle": "human", "count": 3}),
        (MemoryType.OUTCOME, {"action": "Navigate", "route": "Corridor B", "result": "Success"}),
        (MemoryType.OBSERVATION, {"room": "Charging Station", "status": "available"}),
        (MemoryType.OUTCOME, {"action": "Charge", "result": "Success", "gain": 20}),
        (MemoryType.OBSERVATION, {"room": "Room 12", "door": "still closed", "battery": 60}),
    ]
    for i, (rtype, content) in enumerate(experiences, start=4):
        memory.store(MemoryRecord(
            id=f"rec_{i}",
            content=content,
            cycle=i,
            importance=0.5 + i * 0.05,
            record_type=rtype,
        ))
    memory.execute(RobotState(), RuntimeContext())
    print(f"  Stored 5 more records.  Memory size: {memory.episodic.size}")

    # =====================================================================
    # Query by record_type only
    # =====================================================================
    heading("FILTERED QUERY: All observations")

    result = memory.query(MemoryQuery(
        memory_types=[MemoryType.OBSERVATION],
        min_importance=0.0,
        max_results=10,
    ))
    print(f"  Found {len(result.records)} observations:")
    for r in result.records:
        print(f"    [cycle {r.cycle}] {r.content}")

    # =====================================================================
    # Semantic pointer algebra
    # =====================================================================
    heading("SEMANTIC POINTER ALGEBRA")

    robot_sp = encode_content("Robot", dim=128)
    picked_sp = encode_content("picked", dim=128)
    medicine_sp = encode_content("Medicine", dim=128)

    # Encode: Robot (r) picked (p) Medicine (m) via binding: r x p x m
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
    # Consolidation: Episodic -> Logger -> Semantic
    # =====================================================================
    heading("CONSOLIDATION: Episodic -> Logger -> Semantic")

    print("  A busy shift produces many low-importance outcomes. They pile up,")
    print("  fall below the archive threshold, and the Logger compresses them")
    print("  into one narrative per record type.")

    memory = Memory(
        episodic_store=EpisodicStore(FIFOMemoryStrategy(max_size=100)),
        logger=Logger(SPSCALogger(), trigger=CountTrigger(count=5)),
        archive_below=0.6,
    )

    for cycle in range(1, 13):
        memory.store(MemoryRecord(
            id=f"fail_{cycle}",
            content={"action": "OpenDoor", "target": "Room 12", "result": "Failed"},
            cycle=cycle,
            importance=0.4,
            record_type=MemoryType.OUTCOME,
        ))
        memory.execute(RobotState(), RuntimeContext())

    print(f"\n  Episodic records stored:    {memory.episodic.size}")
    print(f"  Semantic narratives:        {memory.semantic.narrative_count}")

    narratives = memory.semantic.query_narratives()
    for n in narratives:
        m = n.compression
        print(f"\n  Narrative '{n.id}' (topic: {n.topic})")
        print(f"    source_ids:      {m.source_ids}")
        print(f"    compression:     {m.method}, confidence={m.confidence:.2f}")
        print(f"    {m.source_count} sources, mean importance={m.mean_importance:.2f}")

    print("\n  -> The Logger compressed {0} episodic records into a single"
          " narrative with provenance.".format(len(narratives[0].source_ids)))

    # =====================================================================
    # Summary
    # =====================================================================
    heading("SUMMARY")
    print(f"  Episodic records:       {memory.episodic.size}")
    print(f"  Semantic narratives:    {memory.semantic.narrative_count}")
    print()
    print("  What works now:")
    print("    - Store observations (from StateEstimation)")
    print("    - Store outcomes (from Execution feedback)")
    print("    - Query by record_type + min_importance filters")
    print("    - Logger compresses episodic records into semantic narratives")
    print("    - Semantic pointer bind/unbind for structured knowledge")
    print()
    print("  What needs a learned encoder for true semantic search:")
    print("    - 'Has this plan failed before?' (partial-text matching)")
    print("    - 'Which route usually succeeds?' (cross-record inference)")
    print("    - Fuzzy similarity across different phrasings")


if __name__ == "__main__":
    main()
