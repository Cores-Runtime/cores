"""Demonstrate Logger consolidation with the hospital delivery scenario.

Shows:
  - Episodic Memory stores outcomes from each delivery attempt
  - Logger compresses archived records into semantic narratives via SPSCA
  - Semantic Memory stores and queries compressed knowledge
  - Planning queries Memory (episodic + semantic merged)

Run:  uv run python demo_logger.py
"""

import sys
sys.path.insert(0, "src")

from cores.core.memory import (
    MemoryRecord,
    MemoryQuery,
    MemoryType,
    EpisodicStore,
    SemanticStore,
)
from cores.core.memory.strategies.fifo_memory import FIFOMemoryStrategy
from cores.core.logger import Logger, SPSCALogger, CountTrigger
from cores.core.runtime_context import RuntimeContext


def heading(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def main() -> None:
    episodic = EpisodicStore(FIFOMemoryStrategy(max_size=1000))
    semantic = SemanticStore()
    logger = Logger(
        strategy=SPSCALogger(),
        trigger=CountTrigger(count=3),
    )

    print("Robot starts hospital delivery rounds.")
    print("Logger consolidates after every 3 new records.\n")

    # ---- Cycle 1: OpenDoor succeeds ----
    heading("CYCLE 1: Open Door -> Success")
    episodic.store(MemoryRecord(
        id="outcome_1",
        content={"action": "OpenDoor", "result": "Success", "target": "Room 12A"},
        cycle=1, importance=0.9, record_type=MemoryType.OUTCOME,
    ))
    episodic.execute(1)
    print(f"  Episodic store size: {episodic.size}")

    # ---- Cycle 2: OpenDoor fails ----
    heading("CYCLE 2: Open Door -> Failed")
    episodic.store(MemoryRecord(
        id="outcome_2",
        content={"action": "OpenDoor", "result": "Failed", "target": "Room 12A"},
        cycle=2, importance=0.8, record_type=MemoryType.OUTCOME,
    ))
    episodic.execute(2)
    print(f"  Episodic store size: {episodic.size}")

    # ---- Cycle 3: Navigate succeeds (triggers logger) ----
    heading("CYCLE 3: Navigate Corridor B -> Success")
    episodic.store(MemoryRecord(
        id="outcome_3",
        content={"action": "Navigate", "result": "Success", "target": "Corridor B"},
        cycle=3, importance=0.9, record_type=MemoryType.OUTCOME,
    ))
    # Archive records below 0.85 importance, then run logger
    episodic.execute(3, archive_below=0.85)
    print(f"  Episodic store size: {episodic.size}")
    if logger.should_run(episodic, RuntimeContext()):
        produced = logger.run(episodic, semantic)
        print(f"  Logger consolidated {produced} narratives")
    print(f"  Semantic narratives: {semantic.narrative_count}")

    # ---- Query semantic knowledge ----
    heading("SEMANTIC KNOWLEDGE")
    narratives = semantic.query_narratives()
    for n in narratives:
        print(f"  [{n.topic}] confidence={n.confidence:.2f} sources={n.content.get('source_count', 0)}")

    # ---- Query merged memory ----
    heading("MERGE QUERY")
    from cores.core.memory import Memory

    memory = Memory(
        episodic_store=episodic,
        semantic_store=semantic,
        logger=logger,
    )
    result = memory.query(MemoryQuery(max_results=10))
    print(f"  Memory returned {len(result.records)} records total")
    for r in result.records:
        print(f"    [{r.cycle}] {r.__class__.__name__}")

    # ---- Summary ----
    heading("SUMMARY")
    print("  Episodic -> Logger -> Semantic pipeline works:")
    print("    1. Execution outcomes stored in Episodic Memory")
    print("    2. CountTrigger fires after 3 records")
    print("    3. Logger compresses archived records via SPSCA")
    print("    4. Semantic Memory stores compressed narratives")
    print("    5. Memory.query() merges episodic + semantic results")


if __name__ == "__main__":
    main()
