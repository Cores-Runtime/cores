"""Smoke tests ensuring benchmark functions execute without error."""

import benchmarks.run_benchmarks as bench


def test_benchmark_event_bus_runs() -> None:
    result = bench.benchmark_event_bus_latency()
    assert result.name == "EventBus"
    assert result.iterations > 0
    assert result.mean_ms >= 0.0


def test_benchmark_scheduler_runs() -> None:
    result = bench.benchmark_scheduler_latency()
    assert result.name == "Scheduler"
    assert result.mean_ms >= 0.0


def test_benchmark_execution_layer_runs() -> None:
    result = bench.benchmark_execution_layer_latency()
    assert result.name == "ExecutionLayer"
    assert result.mean_ms >= 0.0


def test_benchmark_runtime_cycle_runs() -> None:
    result = bench.benchmark_runtime_cycle_latency()
    assert result.name == "Runtime Cycle"
    assert result.mean_ms >= 0.0
