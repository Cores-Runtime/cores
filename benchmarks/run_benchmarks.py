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
    CriticalitySchedulingPolicy,
    DefaultSchedulingPolicy,
    ExecutionLayer,
    ExecutionPlan,
    OperatorSchedulingPolicy,
    RobotState,
    Runtime,
    RuntimeContext,
    Scheduler,
    SimulatedStateEstimator,
)
from cores.events import Event, EventBus, EventType
from cores.interfaces import Module, ModuleProfile, ModuleResult, ModuleStatus


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


@dataclass(frozen=True)
class SchedulerScenario:
    name: str
    state: RobotState
    context: RuntimeContext
    events: List[Event]
    expected_deferred: List[str]
    required_modules: List[str]


@dataclass(frozen=True)
class ScenarioComparisonResult:
    scenario: str
    policy: str
    selected_modules: List[str]
    deferred_modules: List[str]
    mission_utility: float
    safety_coverage: float
    resource_efficiency: float
    decision_time_ms: float


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


class _ScenarioModule(Module):
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


def _build_scheduler_modules() -> List[Module]:
    return [
        _ScenarioModule(
            "safety_monitor",
            priority=100,
            profile=ModuleProfile(
                safety_weight=0.9,
                urgency_weight=0.8,
                compute_cost=0.1,
                time_cost_ms=8.0,
                energy_cost=0.05,
                is_safety_critical=True,
            ),
        ),
        _ScenarioModule(
            "battery_monitor",
            priority=90,
            profile=ModuleProfile(
                safety_weight=0.8,
                urgency_weight=0.7,
                compute_cost=0.05,
                time_cost_ms=5.0,
                energy_cost=0.02,
                is_safety_critical=True,
            ),
        ),
        _ScenarioModule(
            "navigator",
            priority=80,
            profile=ModuleProfile(
                mission_weight=0.8,
                urgency_weight=0.5,
                compute_cost=0.15,
                time_cost_ms=12.0,
                energy_cost=0.08,
                mission_tags=frozenset({"active", "explore"}),
            ),
        ),
        _ScenarioModule(
            "collision_avoidance",
            priority=85,
            profile=ModuleProfile(
                safety_weight=0.85,
                urgency_weight=0.75,
                compute_cost=0.15,
                time_cost_ms=10.0,
                energy_cost=0.06,
                is_safety_critical=True,
            ),
        ),
        _ScenarioModule(
            "localization",
            priority=70,
            profile=ModuleProfile(
                mission_weight=0.7,
                urgency_weight=0.6,
                compute_cost=0.18,
                time_cost_ms=14.0,
                energy_cost=0.08,
                mission_tags=frozenset({"active", "explore"}),
                is_localization=True,
            ),
        ),
        _ScenarioModule(
            "mapper",
            priority=60,
            profile=ModuleProfile(
                mission_weight=0.9,
                compute_cost=0.35,
                time_cost_ms=30.0,
                energy_cost=0.18,
                mission_tags=frozenset({"active", "explore"}),
            ),
        ),
        _ScenarioModule(
            "explorer",
            priority=50,
            profile=ModuleProfile(
                mission_weight=1.0,
                compute_cost=0.45,
                time_cost_ms=35.0,
                energy_cost=0.25,
                mission_tags=frozenset({"active", "explore"}),
            ),
        ),
        _ScenarioModule(
            "diagnostics",
            priority=40,
            profile=ModuleProfile(
                safety_weight=0.7,
                urgency_weight=0.6,
                compute_cost=0.12,
                time_cost_ms=9.0,
                energy_cost=0.04,
                is_diagnostic=True,
            ),
        ),
        _ScenarioModule(
            "recovery",
            priority=30,
            profile=ModuleProfile(
                safety_weight=0.65,
                urgency_weight=0.7,
                compute_cost=0.14,
                time_cost_ms=11.0,
                energy_cost=0.05,
                is_recovery=True,
            ),
        ),
        _ScenarioModule(
            "logger",
            priority=20,
            profile=ModuleProfile(
                mission_weight=0.4,
                compute_cost=0.08,
                time_cost_ms=4.0,
                energy_cost=0.02,
                mission_tags=frozenset({"active", "explore", "idle"}),
            ),
        ),
    ]


def _build_scheduler_scenarios() -> List[SchedulerScenario]:
    return [
        SchedulerScenario(
            name="Scenario A - Nominal Exploration",
            state=RobotState(
                battery_level=1.0,
                mission_status="explore",
            ),
            context=RuntimeContext(compute_budget=1.0, time_budget_ms=100.0),
            events=[],
            expected_deferred=[],
            required_modules=["safety_monitor"],
        ),
        SchedulerScenario(
            name="Scenario B - Low Battery",
            state=RobotState(
                battery_level=0.05,
                mission_status="explore",
            ),
            context=RuntimeContext(compute_budget=1.0, time_budget_ms=100.0),
            events=[],
            expected_deferred=["explorer"],
            required_modules=["safety_monitor", "battery_monitor"],
        ),
        SchedulerScenario(
            name="Scenario C - Obstacle Detected",
            state=RobotState(
                battery_level=0.8,
                mission_status="explore",
                flags={"obstacle_detected": True},
            ),
            context=RuntimeContext(compute_budget=1.0, time_budget_ms=60.0),
            events=[Event(source="proximity", event_type=EventType.DIAGNOSTIC)],
            expected_deferred=["explorer"],
            required_modules=["safety_monitor", "collision_avoidance"],
        ),
        SchedulerScenario(
            name="Scenario D - Emergency Event",
            state=RobotState(
                battery_level=0.5,
                mission_status="explore",
            ),
            context=RuntimeContext(compute_budget=1.0, time_budget_ms=100.0),
            events=[Event(source="runtime", event_type=EventType.SYSTEM_EMERGENCY)],
            expected_deferred=["explorer", "mapper", "logger"],
            required_modules=["safety_monitor", "diagnostics"],
        ),
        SchedulerScenario(
            name="Scenario E - Budget Exhaustion",
            state=RobotState(
                battery_level=0.6,
                mission_status="explore",
            ),
            context=RuntimeContext(compute_budget=0.3, time_budget_ms=20.0),
            events=[],
            expected_deferred=["mapper", "explorer"],
            required_modules=["safety_monitor"],
        ),
        SchedulerScenario(
            name="Scenario G - Sensor Failure",
            state=RobotState(
                battery_level=0.6,
                mission_status="explore",
                sensor_summaries={"gps": "offline", "camera": "degraded"},
                flags={"sensor_failure": True, "hardware_fault": True},
            ),
            context=RuntimeContext(compute_budget=0.6, time_budget_ms=40.0),
            events=[Event(source="gps", event_type=EventType.MODULE_FAILED)],
            expected_deferred=["mapper"],
            required_modules=["diagnostics", "localization"],
        ),
    ]


def _mission_utility(modules: List[Module], selected_names: List[str], mission: str) -> float:
    relevant = [
        module.profile.mission_weight
        for module in modules
        if mission in module.profile.mission_tags
    ]
    if not relevant:
        return 1.0

    selected_weight = sum(
        module.profile.mission_weight
        for module in modules
        if module.name in selected_names and mission in module.profile.mission_tags
    )
    total_weight = sum(relevant)
    return selected_weight / total_weight if total_weight else 1.0


def _safety_coverage(required_modules: List[str], selected_names: List[str]) -> float:
    if not required_modules:
        return 1.0
    satisfied = sum(1 for name in required_modules if name in selected_names)
    return satisfied / len(required_modules)


def _resource_efficiency(
    modules: List[Module],
    selected_names: List[str],
    compute_budget: float,
) -> float:
    useful_compute = sum(
        module.profile.mission_weight + module.profile.safety_weight
        for module in modules
        if module.name in selected_names
    )
    available_compute = max(compute_budget, 1e-6)
    return useful_compute / available_compute


def compare_scheduler_scenarios() -> List[ScenarioComparisonResult]:
    modules = _build_scheduler_modules()
    scenarios = _build_scheduler_scenarios()
    results: List[ScenarioComparisonResult] = []

    for scenario in scenarios:
        for policy_name, policy in (
            ("priority", OperatorSchedulingPolicy()),
            ("criticality", CriticalitySchedulingPolicy()),
        ):
            context = scenario.context.model_copy(deep=True)
            state = scenario.state.model_copy(deep=True)
            plan = policy.schedule(modules, state, context, list(scenario.events))
            selected_names = [module.name for module in plan.modules]
            deferred_names = [
                module.name for module in modules if module.name not in selected_names
            ]
            results.append(
                ScenarioComparisonResult(
                    scenario=scenario.name,
                    policy=policy_name,
                    selected_modules=selected_names,
                    deferred_modules=deferred_names,
                    mission_utility=_mission_utility(
                        modules,
                        selected_names,
                        state.mission_status.lower(),
                    ),
                    safety_coverage=_safety_coverage(
                        scenario.required_modules,
                        selected_names,
                    ),
                    resource_efficiency=_resource_efficiency(
                        modules,
                        selected_names,
                        context.compute_budget,
                    ),
                    decision_time_ms=float(
                        context.metrics.get("decision_time_ms", 0.0)
                    ),
                )
            )

    return results


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


def benchmark_criticality_scheduler_latency() -> BenchmarkResult:
    scheduler = Scheduler(CriticalitySchedulingPolicy())
    modules = _build_scheduler_modules()
    state = RobotState(battery_level=0.6, mission_status="explore")
    context = RuntimeContext(compute_budget=0.6, time_budget_ms=40.0)
    events = [Event(source="gps", event_type=EventType.MODULE_FAILED)]

    def run() -> None:
        scheduler.schedule(modules, state, context, events)

    return _measure("Criticality Scheduler", run, BENCHMARK_ITERATIONS)


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
        benchmark_criticality_scheduler_latency(),
        benchmark_execution_layer_latency(),
        benchmark_runtime_cycle_latency(),
    ]

    for result in results:
        _print_result(result)

    print("\nScheduler Scenario Comparison")
    for comparison in compare_scheduler_scenarios():
        print(
            f"  {comparison.scenario} | {comparison.policy:11} "
            f"| selected={comparison.selected_modules} "
            f"| utility={comparison.mission_utility:.2f} "
            f"| safety={comparison.safety_coverage:.2f} "
            f"| efficiency={comparison.resource_efficiency:.2f}"
        )

    print()


if __name__ == "__main__":
    main()
