"""Benchmark each memory strategy for retrieval latency, growth, and forgetting."""

import time
import statistics
from typing import List

from cores.core.memory import (
    MemoryRecord,
    MemoryQuery,
    FIFOMemoryStrategy,
    TimeDecayMemoryStrategy,
    PriorityMemoryStrategy,
    EpisodicMemoryStrategy,
    SPSCAMemoryStrategy,
)


def make_records(count: int) -> List[MemoryRecord]:
    return [
        MemoryRecord(
            id=f"r{i}",
            content={"value": i, "data": "x" * 50},
            cycle=i,
            importance=abs(hash(str(i))) % 100 / 100.0,
            record_type="observation",
        )
        for i in range(count)
    ]


def bench_retrieval(name: str, strategy, num_records: int, num_queries: int) -> dict:
    records = make_records(num_records)
    for r in records:
        strategy.store(r)

    latencies: List[float] = []
    for _ in range(num_queries):
        q = MemoryQuery(
            query="test",
            min_importance=0.0,
            limit=10,
        )
        start = time.perf_counter()
        strategy.retrieve(q)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed * 1000)

    return {
        "strategy": name,
        "records": num_records,
        "queries": num_queries,
        "avg_latency_ms": round(statistics.mean(latencies), 4),
        "median_latency_ms": round(statistics.median(latencies), 4),
        "max_latency_ms": round(max(latencies), 4),
        "size_after_store": strategy.size,
        "forgetting_time_ms": None,
        "size_after_forget": None,
    }


def bench_forgetting(name: str, strategy_class, num_records: int, **kwargs) -> dict:
    strategy = strategy_class(**kwargs)
    records = make_records(num_records)
    for r in records:
        strategy.store(r)

    start = time.perf_counter()
    forgotten = strategy.forget(current_cycle=num_records)
    elapsed = time.perf_counter() - start

    return {
        "strategy": name,
        "records_before": num_records,
        "records_after": strategy.size,
        "forgotten": forgotten,
        "forgetting_time_ms": round(elapsed * 1000, 4),
    }


def bench_growth(name: str, strategy_class, max_records: int, **kwargs) -> dict:
    strategy = strategy_class(**kwargs)
    sizes: List[int] = []
    for i in range(max_records):
        strategy.store(MemoryRecord(
            id=f"r{i}", content=i, cycle=i, importance=0.5,
        ))
        if i % 100 == 0:
            sizes.append(strategy.size)

    return {
        "strategy": name,
        "max_records": max_records,
        "final_size": strategy.size,
        "bounded": strategy.size <= kwargs.get("max_size", 1000),
    }


def run_all():
    print("=== Memory Strategy Benchmarks ===\n")

    strategies = [
        ("FIFO", FIFOMemoryStrategy, {"max_size": 10000}),
        ("TimeDecay", TimeDecayMemoryStrategy, {"max_size": 10000}),
        ("Priority", PriorityMemoryStrategy, {"max_size": 10000}),
        ("Episodic", EpisodicMemoryStrategy, {"max_episodes": 1000}),
        ("SPSCA", SPSCAMemoryStrategy, {"max_size": 10000, "max_individual": 10000}),
    ]

    print("--- Retrieval Latency (1000 records, 500 queries) ---")
    for name, cls, kwargs in strategies:
        r = bench_retrieval(name, cls(**kwargs), 1000, 500)
        print(f"  {r['strategy']:>10s}: avg={r['avg_latency_ms']:.4f}ms "
              f"med={r['median_latency_ms']:.4f}ms max={r['max_latency_ms']:.4f}ms "
              f"size={r['size_after_store']}")

    print("\n--- Forgetting (10000 records) ---")
    for name, cls, kwargs in strategies:
        r = bench_forgetting(name, cls, 10000, **kwargs)
        print(f"  {r['strategy']:>10s}: before={r['records_before']} "
              f"after={r['records_after']} forgotten={r['forgotten']} "
              f"time={r['forgetting_time_ms']:.4f}ms")

    print("\n--- Memory Growth (5000 records, max_size=1000) ---")
    for name, cls, kwargs in strategies:
        kw = dict(kwargs)
        if name == "Episodic":
            kw = {"max_episodes": 100}
        else:
            kw["max_size"] = 1000
        r = bench_growth(name, cls, 5000, **kw)
        print(f"  {r['strategy']:>10s}: final_size={r['final_size']} "
              f"bounded={r['bounded']}")


if __name__ == "__main__":
    run_all()
