"""Benchmark SPSCALogger compression speed and narrative quality."""

import sys
sys.path.insert(0, "src")

import time
import statistics
from typing import List

from cores.core.memory.interface import MemoryRecord
from cores.core.logger import SPSCALogger


def make_records(count: int) -> List[MemoryRecord]:
    return [
        MemoryRecord(
            id=f"r{i}",
            content={"action": "test", "value": i, "data": "x" * 50},
            cycle=i,
            importance=0.5,
        )
        for i in range(count)
    ]


def bench_compression_speed():
    print("=== SPSCA Compression Benchmarks ===\n")

    for count in [10, 100, 1000]:
        records = make_records(count)
        narr = SPSCALogger()

        latencies: List[float] = []
        for _ in range(20):
            start = time.perf_counter()
            result = narr.compress(records)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed * 1000)

        print(f"  {count:>5} records: avg={statistics.mean(latencies):.4f}ms "
              f"med={statistics.median(latencies):.4f}ms "
              f"narratives={len(result)}")


def bench_narrative_confidence():
    print("\n--- Narrative Confidence ---")
    for count in [1, 5, 10, 50]:
        records = make_records(count)
        narr = SPSCALogger()
        result = narr.compress(records)
        if result:
            conf = result[0].confidence
            print(f"  {count:>3} records: confidence={conf:.3f} "
                  f"source_count={result[0].content.get('source_count', 0)}")
        else:
            print(f"  {count:>3} records: no narratives")


if __name__ == "__main__":
    bench_compression_speed()
    bench_narrative_confidence()
