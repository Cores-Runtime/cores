"""Benchmark the full consolidation pipeline.

Measures the complete path a record takes through memory:

  Store Record -> archive -> trigger -> Logger -> SPSCA -> SemanticStore

Run:  uv run python benchmarks/consolidation_benchmarks.py
"""

import sys
sys.path.insert(0, "src")

import time
import statistics
from typing import List

from cores.core.memory import (
    Memory,
    MemoryRecord,
    MemoryType,
    EpisodicStore,
    FIFOMemoryStrategy,
)
from cores.core.logger import Logger, SPSCALogger, CountTrigger
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


def make_records(count: int) -> List[MemoryRecord]:
    return [
        MemoryRecord(
            id=f"r{i}",
            content={"action": "OpenDoor", "target": "Room 12", "result": "Failed"},
            cycle=i,
            importance=0.4,
            record_type=MemoryType.OUTCOME,
        )
        for i in range(count)
    ]


def bench_consolidation(count: int) -> float:
    """Store `count` records through a low-threshold Memory and return wall time ms."""
    mem = Memory(
        episodic_store=EpisodicStore(FIFOMemoryStrategy(max_size=10_000)),
        logger=Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=25)),
        archive_below=0.6,
    )

    start = time.perf_counter()
    for cycle, record in enumerate(make_records(count)):
        record.cycle = cycle
        mem.store(record)
        mem.execute(RobotState(), RuntimeContext())
    elapsed = (time.perf_counter() - start) * 1000

    return elapsed


def bench_throughput(count: int, runs: int = 5) -> float:
    latencies: List[float] = []
    for _ in range(runs):
        latencies.append(bench_consolidation(count))
    return statistics.median(latencies)


def main():
    print("=== Full Consolidation Pipeline (Episodic -> Logger -> Semantic) ===\n")

    for count in [100, 500, 1000, 5000]:
        median = bench_throughput(count)
        per_record = median / count
        print(f"  {count:>5} records: median={median:8.1f}ms "
              f"({per_record:.4f} ms/record)")

    print("\n--- Semantic output size ---")
    for count in [100, 500, 1000]:
        mem = Memory(
            episodic_store=EpisodicStore(FIFOMemoryStrategy(max_size=10_000)),
            logger=Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=25)),
            archive_below=0.6,
        )
        for cycle, record in enumerate(make_records(count)):
            record.cycle = cycle
            mem.store(record)
            mem.execute(RobotState(), RuntimeContext())
        print(f"  {count:>5} episodic records -> "
              f"{mem.semantic.narrative_count} narratives, "
              f"{mem.episodic.size} remaining")


if __name__ == "__main__":
    main()
