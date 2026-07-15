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


def test_benchmark_criticality_scheduler_runs() -> None:
    result = bench.benchmark_criticality_scheduler_latency()
    assert result.name == "Criticality Scheduler"
    assert result.mean_ms >= 0.0


def test_benchmark_execution_layer_runs() -> None:
    result = bench.benchmark_execution_layer_latency()
    assert result.name == "ExecutionLayer"
    assert result.mean_ms >= 0.0


def test_benchmark_runtime_cycle_runs() -> None:
    result = bench.benchmark_runtime_cycle_latency()
    assert result.name == "Runtime Cycle"
    assert result.mean_ms >= 0.0


def test_scheduler_scenario_comparison_includes_sensor_failure_case() -> None:
    results = bench.compare_scheduler_scenarios()

    sensor_failure_results = [
        result for result in results if result.scenario == "Scenario G - Sensor Failure"
    ]

    assert len(sensor_failure_results) == 2
    assert {result.policy for result in sensor_failure_results} == {
        "priority",
        "criticality",
    }
    criticality_result = next(
        result for result in sensor_failure_results if result.policy == "criticality"
    )
    assert "diagnostics" in criticality_result.selected_modules
    assert "localization" in criticality_result.selected_modules
