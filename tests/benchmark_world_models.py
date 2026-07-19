"""
Benchmark framework for Physicist cognitive node reasoning strategies.

Evaluates how different WorldModelStrategy implementations perform
as the internal reasoning engine of the Physicist.

Measures runtime performance, robotics accuracy, and runtime utility
across all strategies under identical scenarios.
"""

import time
import math
import sys
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from cores.core import (
    WorldModelStrategy,
    SimpleObjectRegistry,
    OccupancyGrid,
    SemanticWorldModel,
    ProbabilisticWorldModel,
    DynamicTrackingWorldModel,
    SSKPM,
    Runtime,
    Scheduler,
    DefaultSchedulingPolicy,
    ExecutionLayer,
)
from cores.interfaces.module import Module, ModuleResult
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


ALL_MODELS: List[str] = [
    "SimpleObjectRegistry",
    "OccupancyGrid",
    "SemanticWorldModel",
    "ProbabilisticWorldModel",
    "DynamicTrackingWorldModel",
    "SSKPM",
]


def _make(name: str) -> WorldModelStrategy:
    return {
        "SimpleObjectRegistry": SimpleObjectRegistry,
        "OccupancyGrid": OccupancyGrid,
        "SemanticWorldModel": SemanticWorldModel,
        "ProbabilisticWorldModel": ProbabilisticWorldModel,
        "DynamicTrackingWorldModel": DynamicTrackingWorldModel,
        "SSKPM": SSKPM,
    }[name]()


@dataclass
class BenchmarkResult:
    model_name: str
    metrics: Dict[str, float] = field(default_factory=dict)


def _measure_latency(fn: Callable, iterations: int = 1000) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    elapsed = time.perf_counter() - start
    return (elapsed / iterations) * 1e6  # microseconds


def benchmark_update_latency(model: WorldModelStrategy, n: int = 100) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    objs = [f"obj_{i}" for i in range(n)]

    def batch_upsert():
        for i, oid in enumerate(objs):
            model.upsert_object(oid, "obstacle", {"x": float(i), "y": float(i * 2)}, 0.9, cycle=i)

    latency = _measure_latency(batch_upsert, iterations=10)
    result.metrics["update_latency_us"] = latency
    result.metrics["objects_after_update"] = model.obstacle_count
    return result


def benchmark_lookup_latency(model: WorldModelStrategy, n: int = 100) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    for i in range(n):
        model.upsert_object(f"obj_{i}", "obstacle", {"x": float(i), "y": float(i * 2)}, 0.9, cycle=i)

    def batch_lookup():
        for i in range(n):
            model.get_object(f"obj_{i}")

    latency = _measure_latency(batch_lookup, iterations=50)
    result.metrics["lookup_latency_us"] = latency
    return result


def benchmark_type_query_latency(model: WorldModelStrategy, n: int = 100) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    for i in range(n // 2):
        model.upsert_object(f"obs_{i}", "obstacle", {"x": float(i), "y": float(i)}, 0.9, cycle=i)
        model.upsert_object(f"wp_{i}", "waypoint", {"x": float(i + 100), "y": float(i)}, 1.0, cycle=i)

    def query():
        model.get_objects_by_type("obstacle")
        model.get_objects_by_type("waypoint")

    latency = _measure_latency(query, iterations=100)
    result.metrics["type_query_latency_us"] = latency
    return result


def benchmark_serialize_size(model: WorldModelStrategy, n: int = 100) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    for i in range(n):
        model.upsert_object(
            f"obj_{i}", "obstacle",
            {"x": float(i), "y": float(i * 2), "z": float(i % 10)},
            0.5 + 0.5 * (i / n), cycle=i,
            properties={"tag": f"type_{i % 5}", "weight": i * 0.1},
        )
    data = model.serialize()
    import json
    serialized = json.dumps(data)
    result.metrics["serialized_bytes"] = len(serialized)
    result.metrics["object_count"] = n
    return result


def benchmark_tracking_accuracy(model: WorldModelStrategy) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    true_positions = []
    estimated_positions = []
    errors = []

    for t in range(20):
        true_x = 0.5 * t
        true_y = 0.25 * t * t
        true_positions.append((true_x, true_y))
        noisy_x = true_x + (0.2 if t < 10 else 0.5)
        noisy_y = true_y + (0.2 if t < 10 else 0.5)
        confidence = 0.9 if t < 10 else 0.5
        model.upsert_object("target", "obstacle", {"x": noisy_x, "y": noisy_y}, confidence, cycle=t)
        obj = model.get_object("target")
        if obj:
            estimated_positions.append((obj.position.get("x", 0), obj.position.get("y", 0)))

    for (tx, ty), (ex, ey) in zip(true_positions, estimated_positions):
        errors.append(math.sqrt((tx - ex) ** 2 + (ty - ey) ** 2))

    result.metrics["mean_tracking_error"] = sum(errors) / max(1, len(errors))
    result.metrics["max_tracking_error"] = max(errors) if errors else 0.0
    result.metrics["tracking_samples"] = len(errors)
    return result


def benchmark_prediction_accuracy(model: WorldModelStrategy) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    predictions = []
    actuals = []

    for t in range(15):
        x = t * 0.5
        y = 0.0
        model.upsert_object("pred_target", "obstacle", {"x": x, "y": y}, 0.95, cycle=t)
        if t >= 3:
            pred = model.predict(steps=3)
            obj_pred = pred.get("predicted_objects", {}).get("pred_target", {})
            pos = obj_pred.get("position", {})
            pred_x = pos.get("x", 0)
            actual_x = (t + 3) * 0.5
            predictions.append(pred_x)
            actuals.append(actual_x)

    if predictions:
        errors = [abs(p - a) for p, a in zip(predictions, actuals)]
        result.metrics["mean_prediction_error"] = sum(errors) / len(errors)
        result.metrics["prediction_steps"] = len(errors)
    return result


def benchmark_stale_removal(model: WorldModelStrategy) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    for i in range(50):
        cycle = i if i < 40 else i + 100
        model.upsert_object(f"obj_{i}", "obstacle", {"x": float(i), "y": float(i)}, 0.9, cycle=cycle)

    start = time.perf_counter()
    removed = model.remove_stale_objects(current_cycle=150, max_age=10)
    elapsed = time.perf_counter() - start

    result.metrics["stale_removed"] = removed
    result.metrics["stale_removal_time_us"] = elapsed * 1e6
    result.metrics["objects_after_cleanup"] = model.obstacle_count
    return result


def benchmark_explain_latency(model: WorldModelStrategy) -> BenchmarkResult:
    result = BenchmarkResult(model_name=type(model).__name__)
    for i in range(20):
        model.upsert_object(f"obj_{i}", "obstacle", {"x": float(i), "y": float(i)}, 0.9, cycle=i)
    model.update_environment(terrain="benchmark", weather="clear")

    def explain():
        model.explain()

    latency = _measure_latency(explain, iterations=100)
    result.metrics["explain_latency_us"] = latency
    return result


def benchmark_runtime_integration(model_name: str) -> BenchmarkResult:
    from cores.core.physicist import Physicist
    result = BenchmarkResult(model_name=model_name)
    model = _make(model_name)
    physicist = Physicist(strategy=model)
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, world_model=model)

    class BMTestModule(Module):
        def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
            context.world_model.upsert_object("bm_obj", "obstacle",
                {"x": context.cycle_count * 2.0, "y": context.cycle_count * 3.0},
                0.85, cycle=context.cycle_count)
            return ModuleResult(module_name=self.name)

    runtime.register_module(BMTestModule("bm_test"))
    start = time.perf_counter()
    for _ in range(10):
        runtime.step()
    elapsed = time.perf_counter() - start

    result.metrics["runtime_step_10_mean_us"] = (elapsed / 10) * 1e6
    result.metrics["runtime_obstacle_count"] = runtime.physicist.strategy.obstacle_count
    return result


def run_all_benchmarks() -> Dict[str, Dict[str, float]]:
    results: Dict[str, Dict[str, float]] = {}

    for name in ALL_MODELS:
        model = _make(name)

        for bench in [
            benchmark_update_latency,
            benchmark_lookup_latency,
            benchmark_type_query_latency,
            benchmark_serialize_size,
            benchmark_tracking_accuracy,
            benchmark_prediction_accuracy,
            benchmark_stale_removal,
            benchmark_explain_latency,
        ]:
            try:
                br = bench(model)
                model = _make(name)
                for k, v in br.metrics.items():
                    results.setdefault(name, {})[k] = v
            except Exception as e:
                results.setdefault(name, {})[f"{bench.__name__}_error"] = str(e)

        try:
            br = benchmark_runtime_integration(name)
            for k, v in br.metrics.items():
                results.setdefault(name, {})[k] = v
        except Exception as e:
            results.setdefault(name, {})["runtime_integration_error"] = str(e)

    return results


def print_results(results: Dict[str, Dict[str, float]]) -> None:
    all_metrics = set()
    for model_results in results.values():
        all_metrics.update(model_results.keys())
    all_metrics = sorted(all_metrics)

    header = f"{'Metric':<40} | " + " | ".join(f"{m:<22}" for m in ALL_MODELS)
    sep = "-" * len(header)

    print("\n=== Physicist Strategy Benchmark Results ===\n")
    print(header)
    print(sep)

    for metric in all_metrics:
        row = f"{metric:<40} | "
        for model in ALL_MODELS:
            val = results.get(model, {}).get(metric, float("nan"))
            if isinstance(val, float):
                row += f"{val:<22.4f}"
            else:
                row += f"{str(val):<22}"
        print(row)

    print("\n=== Best Scores ===\n")
    for metric in all_metrics:
        if metric.endswith("_error") or metric.endswith("_us") or metric.endswith("_bytes"):
            best_model = min(ALL_MODELS, key=lambda m: results.get(m, {}).get(metric, float("inf")))
            best_val = results.get(best_model, {}).get(metric, float("nan"))
            print(f"  {metric}: {best_model} ({best_val:.4f})")
        elif metric == "stale_removed":
            best_model = max(ALL_MODELS, key=lambda m: results.get(m, {}).get(metric, 0))
            best_val = results.get(best_model, {}).get(metric, 0)
            print(f"  {metric}: {best_model} ({best_val:.0f})")


if __name__ == "__main__":
    print("Running Physicist strategy benchmarks...")
    results = run_all_benchmarks()
    print_results(results)
