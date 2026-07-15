"""
CORES Runtime latency benchmarks.

Measures per-component latency using time.perf_counter().
Run from the project root: python benchmarks/run_benchmarks.py
"""

import platform
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Callable, List

from cores.core import (
    DefaultSchedulingPolicy,
    ExecutionLayer,
    ExecutionPlan,
    RobotState,
    Runtime,
    RuntimeContext,
    Scheduler,
    SimulatedStateEstimator,
)
from cores.events import Event, EventBus, EventType
from cores.interfaces import Module, ModuleResult, ModuleStatus


WARMUP_ITERATIONS = 50
BENCHMARK_ITERATIONS = 500


@dataclass
class BenchmarkResult:
    name: str
    mean_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    iterations: int


def _measure(name: str, fn: Callable[[], None], iterations: int) -> BenchmarkResult:
    for _ in range(WARMUP_ITERATIONS):
        fn()

    samples_ms: List[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        samples_ms.append(elapsed_ms)

    sorted_samples = sorted(samples_ms)
    p50_index = len(sorted_samples) // 2

    return BenchmarkResult(
        name=name,
        mean_ms=statistics.mean(sorted_samples),
        min_ms=sorted_samples[0],
        max_ms=sorted_samples[-1],
        p50_ms=sorted_samples[p50_index],
        iterations=iterations,
    )


class _BenchModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


def _build_runtime() -> Runtime:
    modules = [_BenchModule(f"module_{i}") for i in range(5)]
    runtime = Runtime(
        scheduler=Scheduler(DefaultSchedulingPolicy()),
        execution_layer=ExecutionLayer(),
        state_estimator=SimulatedStateEstimator(),
    )
    for module in modules:
        runtime.register_module(module)
    return runtime


def benchmark_event_bus_latency() -> BenchmarkResult:
    event_bus = EventBus()
    received: list[Event] = []
    event_bus.subscribe(EventType.DIAGNOSTIC, received.append)
    event = Event(source="bench", event_type=EventType.DIAGNOSTIC, payload={"v": 1})

    def run() -> None:
        event_bus.publish(event)

    return _measure("EventBus", run, BENCHMARK_ITERATIONS)


def benchmark_scheduler_latency() -> BenchmarkResult:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    modules = [_BenchModule(f"m{i}") for i in range(5)]
    state = RobotState()
    context = RuntimeContext()
    events: list[Event] = []

    def run() -> None:
        scheduler.schedule(modules, state, context, events)

    return _measure("Scheduler", run, BENCHMARK_ITERATIONS)


def benchmark_execution_layer_latency() -> BenchmarkResult:
    layer = ExecutionLayer()
    modules = [_BenchModule(f"m{i}") for i in range(5)]
    plan = ExecutionPlan(modules=modules)
    state = RobotState()
    context = RuntimeContext()

    def run() -> None:
        layer.execute(plan, state, context)

    return _measure("ExecutionLayer", run, BENCHMARK_ITERATIONS)


def benchmark_runtime_cycle_latency() -> BenchmarkResult:
    runtime = _build_runtime()

    def run() -> None:
        runtime.step()

    return _measure("Runtime Cycle", run, BENCHMARK_ITERATIONS)


def _print_result(result: BenchmarkResult) -> None:
    print(f"\n{result.name}")
    print(f"  iterations : {result.iterations}")
    print(f"  mean       : {result.mean_ms:.4f} ms")
    print(f"  p50        : {result.p50_ms:.4f} ms")
    print(f"  min        : {result.min_ms:.4f} ms")
    print(f"  max        : {result.max_ms:.4f} ms")


def main() -> None:
    print("CORES Runtime Benchmarks")
    print(f"Python  : {sys.version.split()[0]}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Warmup  : {WARMUP_ITERATIONS} iterations")
    print(f"Samples : {BENCHMARK_ITERATIONS} iterations per benchmark")

    results = [
        benchmark_event_bus_latency(),
        benchmark_scheduler_latency(),
        benchmark_execution_layer_latency(),
        benchmark_runtime_cycle_latency(),
    ]

    for result in results:
        _print_result(result)

    print()


if __name__ == "__main__":
    main()
