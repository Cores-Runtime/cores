from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from collections import defaultdict

from benchmarks.ablation_study import AblationType, AblationResult, aggregate_ablation_results, compute_ablation_impact
from benchmarks.scenario_generator import GeneratedScenario, generate_scenario_suite
from cores.core import LexicographicRiskAwareSchedulingPolicy
from cores.interfaces import Module
from benchmarks.run_benchmarks import _build_scheduler_modules


def write_ablation_csv(results: List[AblationResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ablation_type", "scenario_name", "safety_coverage", "mission_utility",
            "energy_headroom", "decision_time_ms", "selected_modules"
        ])
        for r in results:
            writer.writerow([
                r.ablation_type.value, r.scenario_name, r.safety_coverage,
                r.mission_utility, r.energy_headroom, r.decision_time_ms,
                ";".join(r.selected_modules)
            ])


def write_ablation_summary_csv(summary: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ablation_type", "count",
            "safety_mean", "safety_std", "safety_min", "safety_max",
            "mission_mean", "mission_std", "mission_min", "mission_max",
            "energy_mean", "energy_std", "energy_min", "energy_max",
            "time_mean", "time_std"
        ])
        for ablation_type, metrics in summary.items():
            writer.writerow([
                ablation_type.value, metrics["count"],
                metrics["safety_coverage"]["mean"], metrics["safety_coverage"]["std"],
                metrics["safety_coverage"]["min"], metrics["safety_coverage"]["max"],
                metrics["mission_utility"]["mean"], metrics["mission_utility"]["std"],
                metrics["mission_utility"]["min"], metrics["mission_utility"]["max"],
                metrics["energy_headroom"]["mean"], metrics["energy_headroom"]["std"],
                metrics["energy_headroom"]["min"], metrics["energy_headroom"]["max"],
                metrics["decision_time_ms"]["mean"], metrics["decision_time_ms"]["std"],
            ])


def write_ablation_impact_csv(impact: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ablation_type",
            "safety_coverage_delta", "mission_utility_delta",
            "energy_headroom_delta", "decision_time_delta",
            "relative_safety", "relative_mission"
        ])
        for ablation_type, metrics in impact.items():
            writer.writerow([
                ablation_type.value,
                metrics["safety_coverage_delta"], metrics["mission_utility_delta"],
                metrics["energy_headroom_delta"], metrics["decision_time_delta"],
                metrics["relative_safety"], metrics["relative_mission"],
            ])


def write_scenario_results_csv(results: List, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    modules = _build_scheduler_modules()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "scenario", "policy", "safety_coverage", "mission_utility",
            "energy_headroom", "decision_time_ms", "resource_efficiency",
            "selected_modules"
        ])
        for r in results:
            total_energy = sum(m.profile.energy_cost for m in modules if m.name in r.selected_modules)
            battery = 1.0
            energy_budget = 0.2 if battery < 0.10 else (0.5 if battery < 0.30 else 1.0)
            energy_headroom = max(0.0, energy_budget - total_energy) / max(energy_budget, 1e-9)
            
            writer.writerow([
                r.scenario, r.policy, r.safety_coverage, r.mission_utility,
                energy_headroom, r.decision_time_ms, r.resource_efficiency,
                ";".join(r.selected_modules)
            ])


def write_aggregate_stats_csv(scenarios_results: Dict, path: Path) -> None:
    import statistics
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "policy", "count",
            "safety_mean", "safety_std", "safety_min", "safety_max",
            "mission_mean", "mission_std", "mission_min", "mission_max",
            "energy_mean", "energy_std", "energy_min", "energy_max",
            "time_mean", "time_std", "time_min", "time_max",
            "efficiency_mean", "efficiency_std"
        ])
        for policy, results in scenarios_results.items():
            safety = [r.safety_coverage for r in results]
            mission = [r.mission_utility for r in results]
            energy = [r.energy_headroom for r in results]
            time = [r.decision_time_ms for r in results]
            efficiency = [r.resource_efficiency for r in results]
            
            writer.writerow([
                policy, len(results),
                statistics.mean(safety), statistics.stdev(safety) if len(safety) > 1 else 0.0,
                min(safety), max(safety),
                statistics.mean(mission), statistics.stdev(mission) if len(mission) > 1 else 0.0,
                min(mission), max(mission),
                statistics.mean(energy), statistics.stdev(energy) if len(energy) > 1 else 0.0,
                min(energy), max(energy),
                statistics.mean(time), statistics.stdev(time) if len(time) > 1 else 0.0,
                min(time), max(time),
                statistics.mean(efficiency), statistics.stdev(efficiency) if len(efficiency) > 1 else 0.0,
            ])


def generate_svg_bar_chart(
    path: Path,
    title: str,
    categories: List[str],
    series: Dict[str, List[float]],
    y_label: str,
    percent_scale: bool = False,
    width: int = 980,
    height: int = 420,
) -> None:
    margin_left = 80
    margin_right = 24
    margin_top = 56
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    all_values = [v for vals in series.values() for v in vals]
    max_value = max(all_values) if all_values else 1.0
    if percent_scale:
        max_value = max(100.0, max_value)
    else:
        max_value = max_value * 1.15 if max_value > 0 else 1.0
    
    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#7c3aed"]
    group_width = plot_width / max(len(categories), 1)
    bar_group_inner = group_width * 0.7
    bar_width = bar_group_inner / max(len(series), 1)
    
    def escape_svg(text: str) -> str:
        return (text.replace("&", "&").replace("<", "<").replace(">", ">"))
    
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" font-size="20" text-anchor="middle" fill="#111827">{escape_svg(title)}</text>',
        f'<text x="20" y="{height/2}" font-size="14" transform="rotate(-90 20 {height/2})" fill="#374151">{escape_svg(y_label)}</text>',
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
            f'<text x="{margin_left + index * group_width + group_width/2:.1f}" y="{height - 30}" font-size="12" text-anchor="middle" fill="#374151">{escape_svg(category)}</text>'
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
            f'<text x="{x + 22}" y="{legend_y + 12}" font-size="12" fill="#374151">{escape_svg(series_name)}</text>'
        )
    
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def generate_svg_line_chart(
    path: Path,
    title: str,
    x_values: List[float],
    series: Dict[str, List[float]],
    x_label: str,
    y_label: str,
    width: int = 980,
    height: int = 420,
) -> None:
    margin_left = 80
    margin_right = 24
    margin_top = 56
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    min_x = min(x_values)
    max_x = max(x_values)
    max_y = max(max(vals) for vals in series.values())
    max_y = max(100.0, max_y)
    
    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#7c3aed"]
    
    def scale_x(value: float) -> float:
        if max_x == min_x:
            return margin_left + plot_width / 2
        return margin_left + ((value - min_x) / (max_x - min_x)) * plot_width
    
    def scale_y(value: float) -> float:
        return margin_top + plot_height - (value / max_y) * plot_height
    
    def escape_svg(text: str) -> str:
        return (text.replace("&", "&").replace("<", "<").replace(">", ">"))
    
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" font-size="20" text-anchor="middle" fill="#111827">{escape_svg(title)}</text>',
        f'<text x="{width/2}" y="{height - 16}" font-size="14" text-anchor="middle" fill="#374151">{escape_svg(x_label)}</text>',
        f'<text x="20" y="{height/2}" font-size="14" transform="rotate(-90 20 {height/2})" fill="#374151">{escape_svg(y_label)}</text>',
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
            f'<text x="{x + 24}" y="{legend_y + 11}" font-size="12" fill="#374151">{escape_svg(series_name)}</text>'
        )
    
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def generate_svg_heatmap(
    path: Path,
    title: str,
    x_labels: List[str],
    y_labels: List[str],
    values: List[List[float]],
    x_label: str,
    y_label: str,
    width: int = 800,
    height: int = 600,
) -> None:
    margin_left = 120
    margin_right = 24
    margin_top = 56
    margin_bottom = 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    cell_width = plot_width / max(len(x_labels), 1)
    cell_height = plot_height / max(len(y_labels), 1)
    
    all_vals = [v for row in values for v in row]
    min_val = min(all_vals) if all_vals else 0.0
    max_val = max(all_vals) if all_vals else 1.0
    
    def escape_svg(text: str) -> str:
        return (text.replace("&", "&").replace("<", "<").replace(">", ">"))
    
    def color_for_value(val: float) -> str:
        if max_val == min_val:
            t = 0.5
        else:
            t = (val - min_val) / (max_val - min_val)
        r = int(255 * t)
        g = int(255 * (1 - t))
        b = 50
        return f"#{r:02x}{g:02x}{b:02x}"
    
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" font-size="20" text-anchor="middle" fill="#111827">{escape_svg(title)}</text>',
        f'<text x="{width/2}" y="{height - 16}" font-size="14" text-anchor="middle" fill="#374151">{escape_svg(x_label)}</text>',
        f'<text x="20" y="{height/2}" font-size="14" transform="rotate(-90 20 {height/2})" fill="#374151">{escape_svg(y_label)}</text>',
    ]
    
    for i, x_label in enumerate(x_labels):
        x = margin_left + i * cell_width + cell_width / 2
        parts.append(
            f'<text x="{x:.1f}" y="{margin_top - 10}" font-size="11" text-anchor="middle" fill="#374151">{escape_svg(x_label)}</text>'
        )
    
    for j, y_label in enumerate(y_labels):
        y = margin_top + j * cell_height + cell_height / 2
        parts.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" font-size="11" text-anchor="end" fill="#374151">{escape_svg(y_label)}</text>'
        )
    
    for j, y_label in enumerate(y_labels):
        for i, x_label in enumerate(x_labels):
            val = values[j][i] if j < len(values) and i < len(values[j]) else 0.0
            color = color_for_value(val)
            x = margin_left + i * cell_width
            y = margin_top + j * cell_height
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_width - 1:.1f}" height="{cell_height - 1:.1f}" fill="{color}"/>'
            )
            label = f"{val:.2f}"
            text_color = "#ffffff" if (val - min_val) / max(max_val - min_val, 1e-9) > 0.5 else "#111827"
            parts.append(
                f'<text x="{x + cell_width/2:.1f}" y="{y + cell_height/2 + 4:.1f}" font-size="10" text-anchor="middle" fill="{text_color}">{label}</text>'
            )
    
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def generate_svg_radar_chart(
    path: Path,
    title: str,
    series: Dict[str, List[float]],
    categories: List[str],
    width: int = 600,
    height: int = 600,
) -> None:
    center_x = width / 2
    center_y = height / 2
    radius = min(width, height) / 2 - 60
    num_axes = len(categories)
    
    def escape_svg(text: str) -> str:
        return (text.replace("&", "&").replace("<", "<").replace(">", ">"))
    
    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#7c3aed"]
    
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{center_x}" y="30" font-size="20" text-anchor="middle" fill="#111827">{escape_svg(title)}</text>',
    ]
    
    for ring in range(5):
        r = radius * (ring + 1) / 5
        points = []
        for i in range(num_axes):
            angle = 2 * math.pi * i / num_axes - math.pi / 2
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<polygon points="{" ".join(points)}" fill="none" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{center_x}" y="{center_y - r - 5}" font-size="10" text-anchor="middle" fill="#6b7280">{(ring + 1) * 20}%</text>'
        )
    
    for i in range(num_axes):
        angle = 2 * math.pi * i / num_axes - math.pi / 2
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        parts.append(
            f'<line x1="{center_x:.1f}" y1="{center_y:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        label_x = center_x + (radius + 20) * math.cos(angle)
        label_y = center_y + (radius + 20) * math.sin(angle)
        parts.append(
            f'<text x="{label_x:.1f}" y="{label_y + 5:.1f}" font-size="11" text-anchor="middle" fill="#374151">{escape_svg(categories[i])}</text>'
        )
    
    for series_index, (series_name, values) in enumerate(series.items()):
        color = colors[series_index % len(colors)]
        points = []
        for i, val in enumerate(values):
            angle = 2 * math.pi * i / num_axes - math.pi / 2
            r = radius * min(val, 1.0)
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<polygon points="{" ".join(points)}" fill="{color}33" stroke="{color}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{center_x + 20:.1f}" y="{center_y + 20 + series_index * 20:.1f}" font-size="12" fill="{color}">{escape_svg(series_name)}</text>'
        )
    
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def generate_svg_pareto_frontier(
    path: Path,
    title: str,
    points: List[Tuple[float, float]],
    labels: List[str],
    x_label: str,
    y_label: str,
    width: int = 600,
    height: int = 600,
) -> None:
    margin_left = 80
    margin_right = 40
    margin_top = 56
    margin_bottom = 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    if max_x == min_x:
        max_x = min_x + 1
    if max_y == min_y:
        max_y = min_y + 1
    
    def scale_x(v: float) -> float:
        return margin_left + (v - min_x) / (max_x - min_x) * plot_width
    
    def scale_y(v: float) -> float:
        return margin_top + plot_height - (v - min_y) / (max_y - min_y) * plot_height
    
    def escape_svg(text: str) -> str:
        return (text.replace("&", "&").replace("<", "<").replace(">", ">"))
    
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" font-size="20" text-anchor="middle" fill="#111827">{escape_svg(title)}</text>',
        f'<text x="{width/2}" y="{height - 16}" font-size="14" text-anchor="middle" fill="#374151">{escape_svg(x_label)}</text>',
        f'<text x="20" y="{height/2}" font-size="14" transform="rotate(-90 20 {height/2})" fill="#374151">{escape_svg(y_label)}</text>',
    ]
    
    for tick in range(6):
        v_x = min_x + (max_x - min_x) * tick / 5
        x = margin_left + tick * plot_width / 5
        parts.append(
            f'<line x1="{x:.1f}" y1="{margin_top}" x2="{x:.1f}" y2="{margin_top + plot_height}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{height - 30}" font-size="11" text-anchor="middle" fill="#6b7280">{v_x:.2f}</text>'
        )
        
        v_y = min_y + (max_y - min_y) * tick / 5
        y = margin_top + tick * plot_height / 5
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + plot_width}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" font-size="11" text-anchor="end" fill="#6b7280">{v_y:.2f}</text>'
        )
    
    for i, (px, py) in enumerate(points):
        x = scale_x(px)
        y = scale_y(py)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#2563eb"/>')
        if i < len(labels):
            parts.append(
                f'<text x="{x + 10:.1f}" y="{y - 5:.1f}" font-size="10" fill="#374151">{escape_svg(labels[i])}</text>'
            )
    
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")