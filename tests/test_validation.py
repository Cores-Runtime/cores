from pathlib import Path

from benchmarks import validation


def test_generate_validation_artifacts_writes_expected_files(tmp_path: Path) -> None:
    artifacts = validation.generate_validation_artifacts(tmp_path)

    assert artifacts.report_path.exists()
    assert artifacts.comparison_csv.exists()
    assert artifacts.sensitivity_csv.exists()
    assert artifacts.ablation_csv.exists()
    assert artifacts.mission_utility_chart.exists()
    assert artifacts.energy_chart.exists()
    assert artifacts.decision_time_chart.exists()
    assert artifacts.sensitivity_chart.exists()
    assert artifacts.ablation_chart.exists()
    assert "Phase 2A.5 Validation Report" in artifacts.report_path.read_text(
        encoding="utf-8"
    )


def test_sensitivity_analysis_covers_requested_weight_sweep() -> None:
    records = validation.run_sensitivity_analysis(values=(0.2, 0.4, 0.6))

    assert {record.weight_value for record in records} == {0.2, 0.4, 0.6}
    assert any(
        record.scenario == "Scenario G - Sensor Failure" and record.weight_value == 0.4
        for record in records
    )


def test_ablation_study_includes_requested_variants() -> None:
    records = validation.run_ablation_study()

    assert {record.variant for record in records} == {
        "full",
        "no_urgency",
        "no_resource_penalty",
    }
