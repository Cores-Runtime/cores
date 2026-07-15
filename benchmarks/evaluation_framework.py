"""
Phase 2A.6 evaluation framework.

This script reruns the existing benchmark scenarios under a revised mission
utility definition that treats utility as a multi-objective evaluation score.
The scheduler implementation is frozen.
"""

from __future__ import annotations

import csv
import platform
import random
import statistics
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Iterable, Sequence

from cores.core import (
    CriticalitySchedulingPolicy,
    OperatorSchedulingPolicy,
    RobotState,
    RuntimeContext,
)
from cores.events import Event, EventType
from cores.interfaces import Module

import run_benchmarks as bench
from validation import write_grouped_bar_chart


DEFAULT_OUTPUT_DIR = Path("benchmarks") / "results" / "phase_2a6"
GENERATED_SCENARIO_COUNT = 100
MONTE_CARLO_TRIALS = 1000
MONTE_CARLO_SEED = 20260715
UTILITY_WEIGHTS = {
    "completion": 0.35,
    "safety": 0.20,
    "energy": 0.15,
    "time": 0.15,
    "preservation": 0.15,
}
SCENARIO_FOCUS = (
    "Scenario A - Nominal Exploration",
    "Scenario B - Low Battery",
    "Scenario G - Sensor Failure",
)


@dataclass(frozen=True)
class UtilityVector:
    completion: float
    safety: float
    energy: float
    time: float
    preservation: float


@dataclass(frozen=True)
class EvaluationRecord:
    scenario: str
    policy: str
    legacy_mission_utility: float
    utility_score: float
    completion: float
    safety: float
    energy: float
    time: float
    preservation: float
    decision_time_ms: float
    selected_modules: list[str]
    deferred_modules: list[str]


@dataclass(frozen=True)
class EvaluationArtifacts:
    output_dir: Path
    report_path: Path
    comparison_csv: Path
    component_csv: Path
    generated_suite_csv: Path
    monte_carlo_csv: Path
    utility_chart: Path
    component_chart: Path
    generated_suite_chart: Path
    monte_carlo_chart: Path


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    state: RobotState
    context: RuntimeContext
    events: list[Event]
    required_modules: list[str]
    cost_scale: float


@dataclass(frozen=True)
class AggregateMetrics:
    policy: str
    sample_count: int
    utility_mean: float
    utility_stdev: float
    utility_ci_low: float
    utility_ci_high: float
    legacy_utility_mean: float
    energy_headroom_mean: float
    safety_coverage_mean: float
    decision_time_ms_mean: float


@dataclass(frozen=True)
class MonteCarloMetrics:
    scenario_set: str
    policy: str
    trial_count: int
    utility_mean: float
    utility_stdev: float
    utility_ci_low: float
    utility_ci_high: float
    legacy_utility_mean: float
    energy_headroom_mean: float
    safety_coverage_mean: float
    decision_time_ms_mean: float


def _legacy_mission_utility(modules: Sequence[Module], selected_names: Sequence[str], mission: str) -> float:
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
    return selected_weight / sum(relevant)


def _mission_completion(modules: Sequence[Module], selected_names: Sequence[str], mission: str) -> float:
    return _legacy_mission_utility(modules, selected_names, mission)


def _safety_coverage(required_modules: Sequence[str], selected_names: Sequence[str]) -> float:
    if not required_modules:
        return 1.0
    satisfied = sum(1 for module_name in required_modules if module_name in selected_names)
    return satisfied / len(required_modules)


def _resource_headroom(used: float, budget: float) -> float:
    if budget <= 0.0:
        return 0.0
    ratio = used / budget
    return max(0.0, 1.0 - ratio)


def _energy_budget_for_battery(battery_level: float) -> float:
    if battery_level < 0.10:
        return 0.2
    if battery_level < 0.30:
        return 0.5
    return 1.0


def _build_scaled_modules(cost_scale: float) -> list[Module]:
    modules: list[Module] = []
    for module in bench._build_scheduler_modules():
        profile = replace(
            module.profile,
            compute_cost=module.profile.compute_cost * cost_scale,
            time_cost_ms=module.profile.time_cost_ms * cost_scale,
            energy_cost=module.profile.energy_cost * cost_scale,
        )
        modules.append(
            bench._ScenarioModule(
                module.name,
                priority=module.priority,
                profile=profile,
            )
        )
    return modules


def _derive_required_modules(state: RobotState, events: Sequence[Event]) -> list[str]:
    required = ["safety_monitor"]
    if state.mission_status.lower() in {"active", "explore"}:
        required.append("localization")
    if state.flags.get("obstacle_detected"):
        required.append("collision_avoidance")
    if state.flags.get("hardware_fault") or state.flags.get("sensor_failure"):
        required.append("diagnostics")
    if state.battery_level < 0.3:
        required.append("battery_monitor")
    if any(event.event_type is EventType.SYSTEM_EMERGENCY for event in events):
        required.extend(["diagnostics", "recovery"])
    seen: set[str] = set()
    ordered: list[str] = []
    for module_name in required:
        if module_name not in seen:
            seen.add(module_name)
            ordered.append(module_name)
    return ordered


def _random_scenario(rng: random.Random, index: int) -> ScenarioSpec:
    battery = round(rng.uniform(0.02, 1.0), 2)
    compute_budget = round(rng.uniform(0.2, 1.0), 2)
    time_budget_ms = round(rng.uniform(10.0, 120.0), 1)
    mission_status = rng.choices(
        ["idle", "active", "explore", "docking"],
        weights=[0.15, 0.35, 0.35, 0.15],
        k=1,
    )[0]
    flags: dict[str, bool] = {}
    if rng.random() < 0.28:
        flags["obstacle_detected"] = True
    if rng.random() < 0.18:
        flags["hardware_fault"] = True
    if rng.random() < 0.22:
        flags["sensor_failure"] = True
    sensor_summaries = {
        "gps": rng.choices(["nominal", "degraded", "offline"], weights=[0.65, 0.2, 0.15], k=1)[0],
        "camera": rng.choices(["nominal", "degraded", "offline"], weights=[0.68, 0.22, 0.1], k=1)[0],
    }
    events: list[Event] = []
    if flags.get("sensor_failure") or flags.get("hardware_fault"):
        events.append(Event(source="sensors", event_type=EventType.MODULE_FAILED))
    if rng.random() < 0.06:
        events.append(Event(source="runtime", event_type=EventType.SYSTEM_EMERGENCY))
    if rng.random() < 0.4:
        events.append(Event(source="state", event_type=EventType.STATE_UPDATED))

    state = RobotState(
        battery_level=battery,
        mission_status=mission_status,
        sensor_summaries=sensor_summaries,
        flags=flags,
    )
    cost_scale = round(rng.uniform(0.7, 1.6), 2)
    return ScenarioSpec(
        name=f"MC-{index:03d}",
        state=state,
        context=RuntimeContext(compute_budget=compute_budget, time_budget_ms=time_budget_ms),
        events=events,
        required_modules=_derive_required_modules(state, events),
        cost_scale=cost_scale,
    )


def generate_scenario_suite(
    count: int = GENERATED_SCENARIO_COUNT,
    seed: int = MONTE_CARLO_SEED,
) -> list[ScenarioSpec]:
    rng = random.Random(seed)
    return [_random_scenario(rng, index) for index in range(count)]


def generate_monte_carlo_trials(
    count: int = MONTE_CARLO_TRIALS,
    seed: int = MONTE_CARLO_SEED + 1,
) -> list[ScenarioSpec]:
    rng = random.Random(seed)
    return [_random_scenario(rng, index) for index in range(count)]


def _compute_vector(
    modules: Sequence[Module],
    selected_names: Sequence[str],
    state: RobotState,
    context: RuntimeContext,
    required_modules: Sequence[str],
) -> UtilityVector:
    selected_modules = [module for module in modules if module.name in selected_names]
    selected_compute = sum(module.profile.compute_cost for module in selected_modules)
    selected_time = sum(module.profile.time_cost_ms for module in selected_modules)
    selected_energy = sum(module.profile.energy_cost for module in selected_modules)

    completion = _mission_completion(modules, selected_names, state.mission_status.lower())
    safety = _safety_coverage(required_modules, selected_names)
    energy = _resource_headroom(selected_energy, _energy_budget_for_battery(state.battery_level))
    time = _resource_headroom(selected_time, context.time_budget_ms)
    preservation = (
        _resource_headroom(selected_compute, context.compute_budget)
        + energy
        + time
    ) / 3.0
    return UtilityVector(
        completion=completion,
        safety=safety,
        energy=energy,
        time=time,
        preservation=preservation,
    )


def _scalarize(vector: UtilityVector) -> float:
    return (
        UTILITY_WEIGHTS["completion"] * vector.completion
        + UTILITY_WEIGHTS["safety"] * vector.safety
        + UTILITY_WEIGHTS["energy"] * vector.energy
        + UTILITY_WEIGHTS["time"] * vector.time
        + UTILITY_WEIGHTS["preservation"] * vector.preservation
    )


class EnergyAwarePriorityPolicy:
    """
    Greedy baseline that respects legacy priorities while accounting for resource cost.
    """

    def schedule(
        self,
        modules: list[Module],
        state: RobotState,
        context: RuntimeContext,
        events: list[Event],
    ) -> bench.ExecutionPlan:
        scored = [
            (
                index,
                module,
                self._score(module, state, context, events),
            )
            for index, module in enumerate(modules)
        ]
        ordered = [
            module
            for index, module, _score in sorted(
                scored,
                key=lambda item: (-item[2], item[0]),
            )
        ]
        selected = self._greedy_select(ordered, state, context)
        return bench.ExecutionPlan(modules=selected)

    def _score(
        self,
        module: Module,
        state: RobotState,
        context: RuntimeContext,
        events: list[Event],
    ) -> float:
        priority_component = float(module.priority)
        if state.battery_level < 0.3:
            priority_component -= module.profile.energy_cost * 80.0
            priority_component -= module.profile.time_cost_ms / max(context.time_budget_ms, 1e-6) * 25.0
        if state.flags.get("hardware_fault"):
            priority_component -= 5.0 if module.profile.is_diagnostic else 0.0
        if any(event.event_type is EventType.SYSTEM_EMERGENCY for event in events):
            priority_component += 10.0 if module.profile.is_safety_critical or module.profile.is_diagnostic else -10.0
        return priority_component

    def _greedy_select(
        self,
        modules: list[Module],
        state: RobotState,
        context: RuntimeContext,
    ) -> list[Module]:
        selected: list[Module] = []
        compute_used = 0.0
        energy_used = 0.0
        time_used = 0.0
        energy_budget = _energy_budget_for_battery(state.battery_level)
        for module in modules:
            next_compute = compute_used + module.profile.compute_cost
            next_energy = energy_used + module.profile.energy_cost
            next_time = time_used + module.profile.time_cost_ms
            if (
                next_compute <= context.compute_budget
                and next_energy <= energy_budget
                and next_time <= context.time_budget_ms
            ):
                selected.append(module)
                compute_used = next_compute
                energy_used = next_energy
                time_used = next_time
        return selected


def _evaluate_policy(
    policy_name: str,
    policy,
    scenario: ScenarioSpec,
    modules: Sequence[Module] | None = None,
) -> EvaluationRecord:
    modules = list(modules or _build_scaled_modules(scenario.cost_scale))
    state = scenario.state.model_copy(deep=True)
    context = scenario.context.model_copy(deep=True)
    started = perf_counter()
    plan = policy.schedule(modules, state, context, list(scenario.events))
    decision_time_ms = (perf_counter() - started) * 1000.0
    selected_names = [module.name for module in plan.modules]
    deferred_names = [module.name for module in modules if module.name not in selected_names]
    vector = _compute_vector(modules, selected_names, state, context, scenario.required_modules)
    return EvaluationRecord(
        scenario=scenario.name,
        policy=policy_name,
        legacy_mission_utility=_legacy_mission_utility(modules, selected_names, state.mission_status.lower()),
        utility_score=_scalarize(vector),
        completion=vector.completion,
        safety=vector.safety,
        energy=vector.energy,
        time=vector.time,
        preservation=vector.preservation,
        decision_time_ms=decision_time_ms,
        selected_modules=selected_names,
        deferred_modules=deferred_names,
    )


def _evaluate_all() -> list[EvaluationRecord]:
    records: list[EvaluationRecord] = []
    for scenario in _build_deterministic_scenarios():
        modules = _build_scaled_modules(scenario.cost_scale)
        records.append(_evaluate_policy("priority", OperatorSchedulingPolicy(), scenario, modules))
        records.append(_evaluate_policy("energy_aware_priority", EnergyAwarePriorityPolicy(), scenario, modules))
        records.append(_evaluate_policy("criticality", CriticalitySchedulingPolicy(), scenario, modules))
    return records


def _evaluate_scenario_suite(
    scenario_specs: Sequence[ScenarioSpec],
) -> list[EvaluationRecord]:
    records: list[EvaluationRecord] = []
    for scenario in scenario_specs:
        modules = _build_scaled_modules(scenario.cost_scale)
        records.append(_evaluate_policy("priority", OperatorSchedulingPolicy(), scenario, modules))
        records.append(_evaluate_policy("energy_aware_priority", EnergyAwarePriorityPolicy(), scenario, modules))
        records.append(_evaluate_policy("criticality", CriticalitySchedulingPolicy(), scenario, modules))
    return records


def _mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _stdev(values: Sequence[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def _ci95(mean: float, stdev: float, sample_count: int) -> tuple[float, float]:
    if sample_count <= 1 or stdev == 0.0:
        return mean, mean
    margin = 1.96 * (stdev / (sample_count ** 0.5))
    return mean - margin, mean + margin


def summarize_records(records: Sequence[EvaluationRecord]) -> list[AggregateMetrics]:
    grouped: dict[str, list[EvaluationRecord]] = {}
    for record in records:
        grouped.setdefault(record.policy, []).append(record)

    summaries: list[AggregateMetrics] = []
    for policy, policy_records in grouped.items():
        utility_values = [record.utility_score for record in policy_records]
        legacy_values = [record.legacy_mission_utility for record in policy_records]
        energy_values = [record.energy for record in policy_records]
        safety_values = [record.safety for record in policy_records]
        decision_values = [record.decision_time_ms for record in policy_records]
        utility_mean = _mean(utility_values)
        utility_stdev = _stdev(utility_values)
        ci_low, ci_high = _ci95(utility_mean, utility_stdev, len(utility_values))
        summaries.append(
            AggregateMetrics(
                policy=policy,
                sample_count=len(policy_records),
                utility_mean=utility_mean,
                utility_stdev=utility_stdev,
                utility_ci_low=ci_low,
                utility_ci_high=ci_high,
                legacy_utility_mean=_mean(legacy_values),
                energy_headroom_mean=_mean(energy_values),
                safety_coverage_mean=_mean(safety_values),
                decision_time_ms_mean=_mean(decision_values),
            )
        )
    return summaries


def summarize_monte_carlo(
    scenario_set: str,
    records: Sequence[EvaluationRecord],
) -> list[MonteCarloMetrics]:
    grouped: dict[str, list[EvaluationRecord]] = {}
    for record in records:
        grouped.setdefault(record.policy, []).append(record)

    summaries: list[MonteCarloMetrics] = []
    for policy, policy_records in grouped.items():
        utility_values = [record.utility_score for record in policy_records]
        utility_mean = _mean(utility_values)
        utility_stdev = _stdev(utility_values)
        ci_low, ci_high = _ci95(utility_mean, utility_stdev, len(utility_values))
        summaries.append(
            MonteCarloMetrics(
                scenario_set=scenario_set,
                policy=policy,
                trial_count=len(policy_records),
                utility_mean=utility_mean,
                utility_stdev=utility_stdev,
                utility_ci_low=ci_low,
                utility_ci_high=ci_high,
                legacy_utility_mean=_mean([record.legacy_mission_utility for record in policy_records]),
                energy_headroom_mean=_mean([record.energy for record in policy_records]),
                safety_coverage_mean=_mean([record.safety for record in policy_records]),
                decision_time_ms_mean=_mean([record.decision_time_ms for record in policy_records]),
            )
        )
    return summaries


def _write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def generate_evaluation_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> EvaluationArtifacts:
    output_dir.mkdir(parents=True, exist_ok=True)
    deterministic_records = _evaluate_all()
    generated_scenarios = generate_scenario_suite()
    generated_records = _evaluate_scenario_suite(generated_scenarios)
    monte_carlo_scenarios = generate_monte_carlo_trials()
    monte_carlo_records = _evaluate_scenario_suite(monte_carlo_scenarios)

    comparison_csv = output_dir / "policy_comparison.csv"
    component_csv = output_dir / "component_breakdown.csv"
    generated_suite_csv = output_dir / "generated_scenario_suite.csv"
    monte_carlo_csv = output_dir / "monte_carlo_trials.csv"
    utility_chart = output_dir / "utility_score_by_scenario.svg"
    component_chart = output_dir / "component_scores_by_scenario.svg"
    generated_suite_chart = output_dir / "generated_suite_means.svg"
    monte_carlo_chart = output_dir / "monte_carlo_means.svg"
    report_path = output_dir / "phase_2a6_evaluation_report.md"

    _write_csv(comparison_csv, [asdict(record) for record in deterministic_records])
    _write_csv(
        component_csv,
        [
            {
                "scenario": record.scenario,
                "policy": record.policy,
                "completion": record.completion,
                "safety": record.safety,
                "energy": record.energy,
                "time": record.time,
                "preservation": record.preservation,
            }
            for record in deterministic_records
        ],
    )
    _write_csv(generated_suite_csv, [asdict(record) for record in generated_records])
    _write_csv(monte_carlo_csv, [asdict(record) for record in monte_carlo_records])

    scenario_order = [scenario.name for scenario in _build_deterministic_scenarios()]
    policies = ("priority", "energy_aware_priority", "criticality")
    by_policy = {policy: [record for record in deterministic_records if record.policy == policy] for policy in policies}
    generated_summary = summarize_records(generated_records)
    monte_carlo_summary = summarize_monte_carlo("monte_carlo_1000", monte_carlo_records)

    write_grouped_bar_chart(
        utility_chart,
        title="Phase 2A.6 Utility Score by Scenario",
        categories=[name.replace("Scenario ", "").replace(" - ", " ") for name in scenario_order],
        series={
            policy.replace("_", " ").title(): [record.utility_score * 100.0 for record in by_policy[policy]]
            for policy in policies
        },
        y_label="Utility Score (%)",
        percent_scale=True,
    )

    write_grouped_bar_chart(
        component_chart,
        title="Phase 2A.6 Focused Component Averages",
        categories=["Completion", "Safety", "Energy", "Time", "Preservation"],
        series={
            policy.replace("_", " ").title(): [
                sum(
                    getattr(record, attr)
                    for record in by_policy[policy]
                    if record.scenario in SCENARIO_FOCUS
                )
                / max(1, sum(1 for record in by_policy[policy] if record.scenario in SCENARIO_FOCUS))
                * 100.0
                for attr in ("completion", "safety", "energy", "time", "preservation")
            ]
            for policy in policies
        },
        y_label="Component Score (%)",
        percent_scale=True,
    )

    write_grouped_bar_chart(
        generated_suite_chart,
        title="Generated Scenario Suite Mean Scores",
        categories=["Utility", "Legacy", "Energy", "Safety"],
        series={
            summary.policy.replace("_", " ").title(): [
                summary.utility_mean * 100.0,
                summary.legacy_utility_mean * 100.0,
                summary.energy_headroom_mean * 100.0,
                summary.safety_coverage_mean * 100.0,
            ]
            for summary in generated_summary
        },
        y_label="Score (%)",
        percent_scale=True,
    )

    write_grouped_bar_chart(
        monte_carlo_chart,
        title="Monte Carlo Mean Scores",
        categories=["Utility", "Legacy", "Energy", "Safety"],
        series={
            summary.policy.replace("_", " ").title(): [
                summary.utility_mean * 100.0,
                summary.legacy_utility_mean * 100.0,
                summary.energy_headroom_mean * 100.0,
                summary.safety_coverage_mean * 100.0,
            ]
            for summary in monte_carlo_summary
        },
        y_label="Score (%)",
        percent_scale=True,
    )

    focus_pairs = {
        scenario: {record.policy: record for record in deterministic_records if record.scenario == scenario}
        for scenario in SCENARIO_FOCUS
    }

    report_lines = [
        "# Phase 2A.6 Evaluation Framework",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Python: `{sys.version.split()[0]}`",
        f"- Platform: `{platform.system()} {platform.machine()}`",
        "",
        "## Purpose",
        "",
        "Re-run the existing benchmark scenarios without modifying the scheduler implementation, but under a revised multi-objective mission-utility definition.",
        "",
        "## Policies Compared",
        "",
        "- `OperatorSchedulingPolicy`",
        "- `EnergyAwarePriorityPolicy`",
        "- `CriticalitySchedulingPolicy`",
        "",
        "## Scalar Utility Weights",
        "",
        "| Component | Weight |",
        "|---|---:|",
    ]
    for name, weight in UTILITY_WEIGHTS.items():
        report_lines.append(f"| {name} | {weight:.2f} |")
    report_lines.extend(
        [
            "",
            "## Deterministic Scenario Comparison",
            "",
            "| Policy | Scenario | Utility Score (%) | Legacy Utility (%) | Completion (%) | Safety (%) | Energy (%) | Time (%) | Preservation (%) |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for record in deterministic_records:
        report_lines.append(
            "| "
            f"{record.policy} | {record.scenario} | "
            f"{record.utility_score * 100.0:.1f} | "
            f"{record.legacy_mission_utility * 100.0:.1f} | "
            f"{record.completion * 100.0:.1f} | "
            f"{record.safety * 100.0:.1f} | "
            f"{record.energy * 100.0:.1f} | "
            f"{record.time * 100.0:.1f} | "
            f"{record.preservation * 100.0:.1f} |"
        )

    report_lines.extend(
        [
            "",
            "## Generated Scenario Suite",
            "",
            f"The generated scenario suite contains `{GENERATED_SCENARIO_COUNT}` deterministic samples spanning battery, hazards, compute budgets, and module cost scales.",
            "",
            "| Policy | Samples | Utility Mean (%) | Utility 95% CI (%) | Legacy Mean (%) | Energy Mean (%) | Safety Mean (%) | Decision Time Mean (ms) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in generated_summary:
        report_lines.append(
            "| "
            f"{summary.policy} | {summary.sample_count} | "
            f"{summary.utility_mean * 100.0:.1f} | "
            f"[{summary.utility_ci_low * 100.0:.1f}, {summary.utility_ci_high * 100.0:.1f}] | "
            f"{summary.legacy_utility_mean * 100.0:.1f} | "
            f"{summary.energy_headroom_mean * 100.0:.1f} | "
            f"{summary.safety_coverage_mean * 100.0:.1f} | "
            f"{summary.decision_time_ms_mean:.4f} |"
        )

    report_lines.extend(
        [
            "",
            "## Monte Carlo Evaluation",
            "",
            f"The Monte Carlo study contains `{MONTE_CARLO_TRIALS}` seeded trials with randomized battery, hazards, compute budget, mission status, and module cost scaling.",
            "",
            "| Policy | Trials | Utility Mean (%) | Utility 95% CI (%) | Legacy Mean (%) | Energy Mean (%) | Safety Mean (%) | Decision Time Mean (ms) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in monte_carlo_summary:
        report_lines.append(
            "| "
            f"{summary.policy} | {summary.trial_count} | "
            f"{summary.utility_mean * 100.0:.1f} | "
            f"[{summary.utility_ci_low * 100.0:.1f}, {summary.utility_ci_high * 100.0:.1f}] | "
            f"{summary.legacy_utility_mean * 100.0:.1f} | "
            f"{summary.energy_headroom_mean * 100.0:.1f} | "
            f"{summary.safety_coverage_mean * 100.0:.1f} | "
            f"{summary.decision_time_ms_mean:.4f} |"
        )

    report_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The revised metric is designed to answer whether a schedule is good for autonomous operation, not merely whether it selected mission-tagged modules.",
            "",
            "The report should be read by comparing utility-score changes against the legacy mission-utility column, then checking whether the stronger baseline closes the gap under larger scenario samples.",
            "",
            "## Focused Takeaways",
            "",
        ]
    )
    priority_scores = [focus_pairs[scenario]["priority"].utility_score for scenario in SCENARIO_FOCUS]
    energy_scores = [focus_pairs[scenario]["energy_aware_priority"].utility_score for scenario in SCENARIO_FOCUS]
    criticality_scores = [focus_pairs[scenario]["criticality"].utility_score for scenario in SCENARIO_FOCUS]
    priority_legacy = [focus_pairs[scenario]["priority"].legacy_mission_utility for scenario in SCENARIO_FOCUS]
    energy_legacy = [focus_pairs[scenario]["energy_aware_priority"].legacy_mission_utility for scenario in SCENARIO_FOCUS]
    criticality_legacy = [focus_pairs[scenario]["criticality"].legacy_mission_utility for scenario in SCENARIO_FOCUS]
    report_lines.extend(
        [
            (
                f"- Average legacy utility: priority `{sum(priority_legacy) / len(priority_legacy) * 100.0:.1f}%`, "
                f"energy-aware priority `{sum(energy_legacy) / len(energy_legacy) * 100.0:.1f}%`, "
                f"criticality `{sum(criticality_legacy) / len(criticality_legacy) * 100.0:.1f}%`."
            ),
            (
                f"- Average revised utility score: priority `{sum(priority_scores) / len(priority_scores) * 100.0:.1f}%`, "
                f"energy-aware priority `{sum(energy_scores) / len(energy_scores) * 100.0:.1f}%`, "
                f"criticality `{sum(criticality_scores) / len(criticality_scores) * 100.0:.1f}%`."
            ),
            "",
            "## Artifacts",
            "",
            "- `policy_comparison.csv`",
            "- `component_breakdown.csv`",
            "- `generated_scenario_suite.csv`",
            "- `monte_carlo_trials.csv`",
            "- `utility_score_by_scenario.svg`",
            "- `component_scores_by_scenario.svg`",
            "- `generated_suite_means.svg`",
            "- `monte_carlo_means.svg`",
        ]
    )

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return EvaluationArtifacts(
        output_dir=output_dir,
        report_path=report_path,
        comparison_csv=comparison_csv,
        component_csv=component_csv,
        generated_suite_csv=generated_suite_csv,
        monte_carlo_csv=monte_carlo_csv,
        utility_chart=utility_chart,
        component_chart=component_chart,
        generated_suite_chart=generated_suite_chart,
        monte_carlo_chart=monte_carlo_chart,
    )


def main() -> None:
    artifacts = generate_evaluation_artifacts()
    print(f"Evaluation artifacts written to {artifacts.output_dir}")


if __name__ == "__main__":
    main()
