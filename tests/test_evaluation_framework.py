from pathlib import Path

from benchmarks import evaluation_framework as eval_fw


def test_generate_evaluation_artifacts_writes_expected_files(tmp_path: Path) -> None:
    artifacts = eval_fw.generate_evaluation_artifacts(tmp_path)

    assert artifacts.report_path.exists()
    assert artifacts.comparison_csv.exists()
    assert artifacts.component_csv.exists()
    assert artifacts.utility_chart.exists()
    assert artifacts.component_chart.exists()
    assert "Phase 2A.6 Evaluation Framework" in artifacts.report_path.read_text(
        encoding="utf-8"
    )


def test_evaluation_records_remain_bounded() -> None:
    records = eval_fw._evaluate_all()

    assert records
    for record in records:
        assert 0.0 <= record.utility_score <= 1.0
        assert 0.0 <= record.completion <= 1.0
        assert 0.0 <= record.safety <= 1.0
        assert 0.0 <= record.energy <= 1.0
        assert 0.0 <= record.time <= 1.0
        assert 0.0 <= record.preservation <= 1.0
