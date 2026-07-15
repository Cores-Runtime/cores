"""
Phase 2A.5 validation pipeline for scheduler research artifacts.

This module generates reproducible comparison tables and SVG charts for:
- policy comparison across benchmark scenarios
- sensitivity analysis for criticality weights
- ablation studies for scoring components
"""

from __future__ import annotations

import csv
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Dict, Iterable, Sequence

from cores.core import (
    CriticalitySchedulingPolicy,
    CriticalityWeights,
    DefaultCriticalityScoringStrategy,
    OperatorSchedulingPolicy,
    RuntimeContext,
)
from cores.interfaces import Module

import run_benchmarks as bench


DEFAULT_OUTPUT_DIR = Path("benchmarks") / "results" / "phase_2a5"
SCENARIO_FOCUS = (
    "Scenario A - Nominal Exploration",
    "Scenario B - Low Battery",
    "Scenario G - Sensor Failure",
)


@dataclass(frozen=True)
class PolicyScenarioMetrics:
    scenario: str
    policy: str
    mission_utility: float
    safety_coverage: float
    energy_consumed: float
    energy_headroom: float
    decision_time_ms: float
    selected_modules: list[str]
    deferred_modules: list[str]


@dataclass(frozen=True)
class SensitivityMetrics:
    scenario: str
    varied_weight: str
    weight_value: float
    mission_utility: float
    energy_headroom: float


@dataclass(frozen=True)
class AblationMetrics:
    scenario: str
    variant: str
    mission_utility: float
    energy_headroom: float
    decision_time_ms: float


@dataclass(frozen=True)
class ValidationArtifacts:
    output_dir: Path
    report_path: Path
    comparison_csv: Path
    sensitivity_csv: Path
    ablation_csv: Path
    mission_utility_chart: Path
    energy_chart: Path
    decision_time_chart: Path
    sensitivity_chart: Path
    ablation_chart: Path


def energy_budget_for_battery(battery_level: float) -> float:
    if battery_level < 0.10:
        return 0.2
    if battery_level < 0.30:
        return 0.5
    return 1.0


def mission_utility(modules: Sequence[Module], selected_names: Sequence[str], mission: str) -> float:
    relevant_weights = [
        module.profile.mission_weight
        for module in modules
        if mission in module.profile.mission_tags
    ]
    if not relevant_weights:
        return 1.0

    selected_weight = sum(
        module.profile.mission_weight
        for module in modules
        if module.name in selected_names and mission in module.profile.mission_tags
    )
    return selected_weight / sum(relevant_weights)


def safety_coverage(required_modules: Sequence[str], selected_names: Sequence[str]) -> float:
    if not required_modules:
        return 1.0
    satisfied = sum(1 for module_name in required_modules if module_name in selected_names)
    return satisfied / len(required_modules)


def energy_metrics(modules: Sequence[Module], selected_names: Sequence[str], battery_level: float) -> tuple[float, float]:
    consumed = sum(
        module.profile.energy_cost
        for module in modules
        if module.name in selected_names
    )
    budget = energy_budget_for_battery(battery_level)
    headroom = max(0.0, budget - consumed) / budget if budget > 0.0 else 0.0
    return consumed, headroom


def evaluate_policy(policy_name: str, policy, scenario: bench.SchedulerScenario) -> PolicyScenarioMetrics:
    modules = bench._build_scheduler_modules()
    state = scenario.state.model_copy(deep=True)
    context = scenario.context.model_copy(deep=True)
    start = perf_counter()
    plan = policy.schedule(modules, state, context, list(scenario.events))
    decision_time_ms = (perf_counter() - start) * 1000.0
    selected_names = [module.name for module in plan.modules]
    deferred_names = [module.name for module in modules if module.name not in selected_names]
    energy_consumed, energy_headroom = energy_metrics(
        modules,
        selected_names,
        state.battery_level,
    )
    return PolicyScenarioMetrics(
        scenario=scenario.name,
        policy=policy_name,
        mission_utility=mission_utility(modules, selected_names, state.mission_status.lower()),
        safety_coverage=safety_coverage(scenario.required_modules, selected_names),
        energy_consumed=energy_consumed,
        energy_headroom=energy_headroom,
        decision_time_ms=decision_time_ms,
        selected_modules=selected_names,
        deferred_modules=deferred_names,
    )


def compare_policies() -> list[PolicyScenarioMetrics]:
    results: list[PolicyScenarioMetrics] = []
    for scenario in bench._build_scheduler_scenarios():
        results.append(evaluate_policy("priority", OperatorSchedulingPolicy(), scenario))
        results.append(
            evaluate_policy("criticality", CriticalitySchedulingPolicy(), scenario)
        )
    return results


def normalized_weight_variant(
    weight_name: str,
    target_value: float,
    baseline: CriticalityWeights | None = None,
) -> CriticalityWeights:
    base = baseline or CriticalityWeights()
    base_values = {
        "safety": base.safety,
        "mission": base.mission,
        "urgency": base.urgency,
        "resource_penalty": base.resource_penalty,
    }
    remaining_keys = [key for key in base_values if key != weight_name]
    remaining_total = sum(base_values[key] for key in remaining_keys)
    scale = 0.0 if remaining_total == 0.0 else (1.0 - target_value) / remaining_total
    updated = {
        key: (target_value if key == weight_name else base_values[key] * scale)
        for key in base_values
    }
    return CriticalityWeights(
        safety=updated["safety"],
        mission=updated["mission"],
        urgency=updated["urgency"],
        resource_penalty=updated["resource_penalty"],
    )


def run_sensitivity_analysis(
    weight_name: str = "safety",
    values: Sequence[float] = (0.2, 0.35, 0.4, 0.6),
) -> list[SensitivityMetrics]:
    records: list[SensitivityMetrics] = []
    for value in values:
        weights = normalized_weight_variant(weight_name, value)
        policy = CriticalitySchedulingPolicy(
            scoring_strategy=DefaultCriticalityScoringStrategy(weights=weights)
        )
        for scenario in bench._build_scheduler_scenarios():
            result = evaluate_policy(f"criticality_{weight_name}_{value:.2f}", policy, scenario)
            records.append(
                SensitivityMetrics(
                    scenario=scenario.name,
                    varied_weight=weight_name,
                    weight_value=value,
                    mission_utility=result.mission_utility,
                    energy_headroom=result.energy_headroom,
                )
            )
    return records


def ablated_weights(variant: str, baseline: CriticalityWeights | None = None) -> CriticalityWeights:
    base = baseline or CriticalityWeights()
    if variant == "full":
        return base
    if variant == "no_urgency":
        return normalized_weight_variant("urgency", 0.0, base)
    if variant == "no_resource_penalty":
        return normalized_weight_variant("resource_penalty", 0.0, base)
    raise ValueError(f"Unknown ablation variant: {variant}")


def run_ablation_study() -> list[AblationMetrics]:
    records: list[AblationMetrics] = []
    for variant in ("full", "no_urgency", "no_resource_penalty"):
        policy = CriticalitySchedulingPolicy(
            scoring_strategy=DefaultCriticalityScoringStrategy(
                weights=ablated_weights(variant)
            )
        )
        for scenario in bench._build_scheduler_scenarios():
            result = evaluate_policy(variant, policy, scenario)
            records.append(
                AblationMetrics(
                    scenario=scenario.name,
                    variant=variant,
                    mission_utility=result.mission_utility,
                    energy_headroom=result.energy_headroom,
                    decision_time_ms=result.decision_time_ms,
                )
            )
    return records


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _svg_text(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def write_grouped_bar_chart(
    path: Path,
    *,
    title: str,
    categories: Sequence[str],
    series: Dict[str, Sequence[float]],
    y_label: str,
    percent_scale: bool = False,
) -> None:
    width = 980
    height = 420
    margin_left = 80
    margin_right = 24
    margin_top = 56
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    max_value = max(max(values) for values in series.values())
    if percent_scale:
        max_value = max(100.0, max_value)
    else:
        max_value = max_value * 1.15 if max_value > 0 else 1.0

    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea"]
    group_width = plot_width / max(len(categories), 1)
    bar_group_inner = group_width * 0.7
    bar_width = bar_group_inner / max(len(series), 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" font-size="20" text-anchor="middle" fill="#111827">{_svg_text(title)}</text>',
        f'<text x="20" y="{height/2}" font-size="14" transform="rotate(-90 20 {height/2})" fill="#374151">{_svg_text(y_label)}</text>',
    ]

    for tick in range(6):
        value = max_value * tick / 5
        y = margin_top + plot_height - (plot_height * tick / 5)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        label = f"{value:.0f}" if percent_scale else f"{value:.3f}"
        parts.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" font-size="12" text-anchor="end" fill="#6b7280">{label}</text>'
        )

    for index, category in enumerate(categories):
        group_start = margin_left + index * group_width + (group_width - bar_group_inner) / 2
        parts.append(
            f'<text x="{margin_left + index * group_width + group_width/2:.1f}" y="{height - 30}" font-size="12" text-anchor="middle" fill="#374151">{_svg_text(category)}</text>'
        )
        for series_index, (series_name, values) in enumerate(series.items()):
            value = values[index]
            bar_height = 0.0 if max_value == 0 else (value / max_value) * plot_height
            x = group_start + series_index * bar_width
            y = margin_top + plot_height - bar_height
            color = colors[series_index % len(colors)]
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 6:.1f}" height="{bar_height:.1f}" fill="{color}" rx="2"/>'
            )
            label = f"{value:.1f}" if percent_scale else f"{value:.4f}"
            parts.append(
                f'<text x="{x + (bar_width - 6) / 2:.1f}" y="{max(y - 6, margin_top + 12):.1f}" font-size="11" text-anchor="middle" fill="#111827">{label}</text>'
            )

    legend_x = margin_left
    legend_y = height - 56
    for series_index, series_name in enumerate(series):
        color = colors[series_index % len(colors)]
        x = legend_x + series_index * 180
        parts.append(f'<rect x="{x}" y="{legend_y}" width="14" height="14" fill="{color}" rx="2"/>')
        parts.append(
            f'<text x="{x + 22}" y="{legend_y + 12}" font-size="12" fill="#374151">{_svg_text(series_name)}</text>'
        )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_line_chart(
    path: Path,
    *,
    title: str,
    x_values: Sequence[float],
    series: Dict[str, Sequence[float]],
    x_label: str,
    y_label: str,
) -> None:
    width = 980
    height = 420
    margin_left = 80
    margin_right = 24
    margin_top = 56
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    min_x = min(x_values)
    max_x = max(x_values)
    max_y = max(max(values) for values in series.values())
    max_y = max(100.0, max_y)
    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#7c3aed"]

    def scale_x(value: float) -> float:
        if max_x == min_x:
            return margin_left + plot_width / 2
        return margin_left + ((value - min_x) / (max_x - min_x)) * plot_width

    def scale_y(value: float) -> float:
        return margin_top + plot_height - (value / max_y) * plot_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" font-size="20" text-anchor="middle" fill="#111827">{_svg_text(title)}</text>',
        f'<text x="{width/2}" y="{height - 16}" font-size="14" text-anchor="middle" fill="#374151">{_svg_text(x_label)}</text>',
        f'<text x="20" y="{height/2}" font-size="14" transform="rotate(-90 20 {height/2})" fill="#374151">{_svg_text(y_label)}</text>',
    ]

    for tick in range(6):
        value = max_y * tick / 5
        y = scale_y(value)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" font-size="12" text-anchor="end" fill="#6b7280">{value:.0f}</text>'
        )

    for x_value in x_values:
        x = scale_x(x_value)
        parts.append(
            f'<line x1="{x:.1f}" y1="{margin_top}" x2="{x:.1f}" y2="{margin_top + plot_height}" stroke="#f3f4f6" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{height - 36}" font-size="12" text-anchor="middle" fill="#6b7280">{x_value:.2f}</text>'
        )

    for series_index, (series_name, y_values) in enumerate(series.items()):
        color = colors[series_index % len(colors)]
        points = " ".join(
            f"{scale_x(x):.1f},{scale_y(y):.1f}" for x, y in zip(x_values, y_values, strict=True)
        )
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{points}"/>'
        )
        for x, y in zip(x_values, y_values, strict=True):
            cx = scale_x(x)
            cy = scale_y(y)
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{color}"/>')

    legend_x = margin_left
    legend_y = height - 60
    for series_index, series_name in enumerate(series):
        color = colors[series_index % len(colors)]
        x = legend_x + series_index * 130
        parts.append(f'<line x1="{x}" y1="{legend_y + 7}" x2="{x + 18}" y2="{legend_y + 7}" stroke="{color}" stroke-width="3"/>')
        parts.append(
            f'<text x="{x + 24}" y="{legend_y + 11}" font-size="12" fill="#374151">{_svg_text(series_name)}</text>'
        )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _scenario_label(full_name: str) -> str:
    return full_name.replace("Scenario ", "").replace(" - ", " ")


def summarize_policy_improvements(records: Sequence[PolicyScenarioMetrics]) -> dict[str, float]:
    grouped: dict[str, dict[str, PolicyScenarioMetrics]] = {}
    for record in records:
        grouped.setdefault(record.scenario, {})[record.policy] = record

    mission_deltas = []
    energy_deltas = []
    for scenario in SCENARIO_FOCUS:
        pair = grouped[scenario]
        priority = pair["priority"]
        criticality = pair["criticality"]
        mission_deltas.append(criticality.mission_utility - priority.mission_utility)
        energy_deltas.append(criticality.energy_headroom - priority.energy_headroom)

    return {
        "avg_mission_utility_delta_pct": (sum(mission_deltas) / len(mission_deltas)) * 100.0,
        "avg_energy_headroom_delta_pct": (sum(energy_deltas) / len(energy_deltas)) * 100.0,
    }


def generate_validation_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> ValidationArtifacts:
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison = compare_policies()
    sensitivity = run_sensitivity_analysis()
    ablation = run_ablation_study()

    comparison_csv = output_dir / "policy_comparison.csv"
    sensitivity_csv = output_dir / "sensitivity_safety_weight.csv"
    ablation_csv = output_dir / "ablation_study.csv"
    mission_chart = output_dir / "policy_mission_utility.svg"
    energy_chart = output_dir / "policy_energy_headroom.svg"
    decision_chart = output_dir / "policy_decision_time.svg"
    sensitivity_chart = output_dir / "sensitivity_safety_weight.svg"
    ablation_chart = output_dir / "ablation_mission_utility.svg"
    report_path = output_dir / "phase_2a5_validation_report.md"

    write_csv(comparison_csv, [asdict(row) for row in comparison])
    write_csv(sensitivity_csv, [asdict(row) for row in sensitivity])
    write_csv(ablation_csv, [asdict(row) for row in ablation])

    scenario_order = [scenario.name for scenario in bench._build_scheduler_scenarios()]
    comparison_by_policy = {
        policy: [row for row in comparison if row.policy == policy]
        for policy in ("priority", "criticality")
    }

    write_grouped_bar_chart(
        mission_chart,
        title="Mission Utility by Scenario",
        categories=[_scenario_label(name) for name in scenario_order],
        series={
            policy.title(): [
                record.mission_utility * 100.0 for record in comparison_by_policy[policy]
            ]
            for policy in ("priority", "criticality")
        },
        y_label="Mission Utility (%)",
        percent_scale=True,
    )
    write_grouped_bar_chart(
        energy_chart,
        title="Energy Headroom by Scenario",
        categories=[_scenario_label(name) for name in scenario_order],
        series={
            policy.title(): [
                record.energy_headroom * 100.0 for record in comparison_by_policy[policy]
            ]
            for policy in ("priority", "criticality")
        },
        y_label="Energy Headroom (%)",
        percent_scale=True,
    )
    write_grouped_bar_chart(
        decision_chart,
        title="Scheduler Decision Time by Scenario",
        categories=[_scenario_label(name) for name in scenario_order],
        series={
            policy.title(): [
                record.decision_time_ms for record in comparison_by_policy[policy]
            ]
            for policy in ("priority", "criticality")
        },
        y_label="Decision Time (ms)",
    )

    sensitivity_values = sorted({record.weight_value for record in sensitivity})
    sensitivity_series: dict[str, list[float]] = {}
    for scenario_name in scenario_order:
        if scenario_name not in SCENARIO_FOCUS:
            continue
        sensitivity_series[_scenario_label(scenario_name)] = [
            next(
                record.mission_utility * 100.0
                for record in sensitivity
                if record.scenario == scenario_name and record.weight_value == value
            )
            for value in sensitivity_values
        ]
    sensitivity_series["Average"] = [
        sum(
            next(
                record.mission_utility * 100.0
                for record in sensitivity
                if record.scenario == scenario_name and record.weight_value == value
            )
            for scenario_name in SCENARIO_FOCUS
        )
        / len(SCENARIO_FOCUS)
        for value in sensitivity_values
    ]
    write_line_chart(
        sensitivity_chart,
        title="Safety Weight Sensitivity vs Mission Utility",
        x_values=sensitivity_values,
        series=sensitivity_series,
        x_label="Safety Weight (wS)",
        y_label="Mission Utility (%)",
    )

    ablation_variants = ("full", "no_urgency", "no_resource_penalty")
    ablation_series = {
        variant.replace("_", " ").title(): [
            (
                sum(
                    record.mission_utility * 100.0
                    for record in ablation
                    if record.variant == variant and record.scenario in SCENARIO_FOCUS
                )
                / len(SCENARIO_FOCUS)
            )
        ]
        for variant in ablation_variants
    }
    write_grouped_bar_chart(
        ablation_chart,
        title="Ablation Study: Average Mission Utility",
        categories=["Focused Scenarios"],
        series=ablation_series,
        y_label="Mission Utility (%)",
        percent_scale=True,
    )

    improvement_summary = summarize_policy_improvements(comparison)
    generated_at = datetime.now(timezone.utc).isoformat()

    report_lines = [
        "# Phase 2A.5 Validation Report",
        "",
        f"- Generated: `{generated_at}`",
        f"- Python: `{sys.version.split()[0]}`",
        f"- Platform: `{platform.system()} {platform.machine()}`",
        "",
        "## Policy Comparison",
        "",
        "| Policy | Scenario | Mission Utility (%) | Energy Headroom (%) | Decision Time (ms) | Safety Coverage (%) |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for record in comparison:
        report_lines.append(
            "| "
            f"{record.policy} | {record.scenario} | "
            f"{record.mission_utility * 100.0:.1f} | "
            f"{record.energy_headroom * 100.0:.1f} | "
            f"{record.decision_time_ms:.4f} | "
            f"{record.safety_coverage * 100.0:.1f} |"
        )

    report_lines.extend(
        [
            "",
            "## Key Findings",
            "",
            (
                f"- Criticality changed average mission utility across the focused scenarios "
                f"(Normal, Low Battery, Sensor Failure) by "
                f"`{improvement_summary['avg_mission_utility_delta_pct']:+.1f}%`."
            ),
            (
                f"- Criticality changed average energy headroom across the same scenarios by "
                f"`{improvement_summary['avg_energy_headroom_delta_pct']:+.1f}%`."
            ),
            "- Safety coverage is reported alongside utility and energy so scheduler gains are not interpreted in isolation.",
            "",
            "## Sensitivity Analysis",
            "",
            "The safety weight sweep varies `wS` while renormalizing the other weights to keep the total at `1.0`.",
            "",
            "| Scenario | wS | Mission Utility (%) | Energy Headroom (%) |",
            "|---|---:|---:|---:|",
        ]
    )

    for record in sensitivity:
        if record.scenario not in SCENARIO_FOCUS:
            continue
        report_lines.append(
            f"| {record.scenario} | {record.weight_value:.2f} | "
            f"{record.mission_utility * 100.0:.1f} | {record.energy_headroom * 100.0:.1f} |"
        )

    report_lines.extend(
        [
            "",
            "## Ablation Study",
            "",
            "Ablations remove one scoring component at a time and renormalize the remaining weights.",
            "",
            "| Variant | Scenario | Mission Utility (%) | Energy Headroom (%) | Decision Time (ms) |",
            "|---|---|---:|---:|---:|",
        ]
    )

    for record in ablation:
        if record.scenario not in SCENARIO_FOCUS:
            continue
        report_lines.append(
            f"| {record.variant} | {record.scenario} | "
            f"{record.mission_utility * 100.0:.1f} | "
            f"{record.energy_headroom * 100.0:.1f} | "
            f"{record.decision_time_ms:.4f} |"
        )

    report_lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- `policy_comparison.csv`",
            f"- `sensitivity_safety_weight.csv`",
            f"- `ablation_study.csv`",
            f"- `policy_mission_utility.svg`",
            f"- `policy_energy_headroom.svg`",
            f"- `policy_decision_time.svg`",
            f"- `sensitivity_safety_weight.svg`",
            f"- `ablation_mission_utility.svg`",
        ]
    )

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    return ValidationArtifacts(
        output_dir=output_dir,
        report_path=report_path,
        comparison_csv=comparison_csv,
        sensitivity_csv=sensitivity_csv,
        ablation_csv=ablation_csv,
        mission_utility_chart=mission_chart,
        energy_chart=energy_chart,
        decision_time_chart=decision_chart,
        sensitivity_chart=sensitivity_chart,
        ablation_chart=ablation_chart,
    )


def main() -> None:
    artifacts = generate_validation_artifacts()
    print(f"Validation artifacts written to {artifacts.output_dir}")


if __name__ == "__main__":
    main()
