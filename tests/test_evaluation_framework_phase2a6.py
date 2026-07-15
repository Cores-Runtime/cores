from pathlib import Path

from benchmarks import evaluation_framework as eval_fw


def test_phase_2a6_artifacts_are_generated(tmp_path: Path) -> None:
    artifacts = eval_fw.generate_evaluation_artifacts(tmp_path)

    assert artifacts.report_path.exists()
    assert artifacts.comparison_csv.exists()
    assert artifacts.component_csv.exists()
    assert artifacts.generated_suite_csv.exists()
    assert artifacts.monte_carlo_csv.exists()
    assert artifacts.utility_chart.exists()
    assert artifacts.component_chart.exists()
    assert artifacts.generated_suite_chart.exists()
    assert artifacts.monte_carlo_chart.exists()
    assert "Phase 2A.6 Evaluation Framework" in artifacts.report_path.read_text(
        encoding="utf-8"
    )
    assert "EnergyAwarePriorityPolicy" in artifacts.report_path.read_text(
        encoding="utf-8"
    )


def test_phase_2a6_utility_weights_sum_to_one() -> None:
    assert abs(sum(eval_fw.UTILITY_WEIGHTS.values()) - 1.0) < 1e-9


def test_phase_2a6_generated_suite_has_expected_size() -> None:
    scenarios = eval_fw.generate_scenario_suite()
    assert len(scenarios) == eval_fw.GENERATED_SCENARIO_COUNT


def test_phase_2a6_monte_carlo_has_expected_size() -> None:
    scenarios = eval_fw.generate_monte_carlo_trials()
    assert len(scenarios) == eval_fw.MONTE_CARLO_TRIALS


def test_phase_2a6_summaries_include_stronger_baseline() -> None:
    records = eval_fw._evaluate_all()
    policies = {record.policy for record in records}

    assert {
        "priority",
        "energy_aware_priority",
        "criticality",
    } <= policies


def test_energy_aware_priority_prefers_lower_cost_modules_under_pressure() -> None:
    policy = eval_fw.EnergyAwarePriorityPolicy()
    scenario = eval_fw._build_deterministic_scenarios()[1]
    modules = eval_fw._build_scaled_modules(scenario.cost_scale)

    plan = policy.schedule(modules, scenario.state, scenario.context, list(scenario.events))
    selected_names = [module.name for module in plan.modules]

    assert "safety_monitor" in selected_names
    assert "explorer" not in selected_names
