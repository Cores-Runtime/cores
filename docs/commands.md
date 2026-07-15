# CORES Command Reference

All commands are run from the `cores/` project root, where `pyproject.toml` lives.

## Environment Setup

### Install the package in editable mode

```bash
pip install -e .
```

Installs `cores-runtime` from `src/` and keeps local edits live without reinstalling.

### Install with development dependencies

```bash
pip install -e ".[dev]"
```

Installs the runtime plus `pytest`, `ruff`, and `mypy`.

## Testing

### Run the full test suite

```bash
python -m pytest
```

Discovers and runs all tests under `tests/`.

### Run tests with verbose output

```bash
python -m pytest -v
```

Shows each test name and status.

### Stop on the first failure

```bash
python -m pytest -x
```

Useful when iterating on a single failing change.

### Show locals for failing tests

```bash
python -m pytest -l
```

Prints local variable state at the point of failure.

### Run one test file

```bash
python -m pytest tests/test_criticality_policy.py
```

Runs only the named test module.

### Run tests by keyword

```bash
python -m pytest -k "sensor_failure"
```

Filters the test run by substring expression.

## Linting

### Lint the source tree

```bash
python -m ruff check src tests
```

Runs Ruff checks across runtime and test code.

### Auto-fix Ruff issues where safe

```bash
python -m ruff check src tests --fix
```

Applies fixable lint corrections.

## Type Checking

### Run mypy on the runtime package

```bash
python -m mypy src
```

Performs static type checking on the runtime source.

## Benchmarks

### Run microbenchmarks

```bash
python benchmarks/run_benchmarks.py
```

Runs latency-oriented benchmarks for the EventBus, scheduler, execution layer, runtime cycle, and scenario comparison summary.

### Generate Phase 2A.5 validation artifacts

```bash
python benchmarks/validation.py
```

Generates policy-comparison CSVs, sensitivity-analysis CSVs, ablation-study CSVs, SVG charts, and a Markdown validation report under `benchmarks/results/phase_2a5/`.

### Generate Phase 2A.6 evaluation artifacts

```bash
python benchmarks/evaluation_framework.py
```

Re-runs the benchmark scenarios under the revised multi-objective mission-utility definition, compares against `EnergyAwarePriorityPolicy`, generates a 100-scenario deterministic suite, runs a 1000-trial Monte Carlo study, and writes comparison CSVs, summary CSVs, SVG charts, and a Markdown evaluation report under `benchmarks/results/phase_2a6/`.

### Review Experiment Report v1

```bash
Get-Content research/experiment_001.md
```

Prints the first experiment report that summarizes the current hypothesis, method, results, discussion, and conclusion.

## Quality Gate

### Run the standard pre-commit check

```bash
python -m ruff check src tests && python -m pytest
```

Runs linting and then the full test suite.

### Run validation after tests

```bash
python -m pytest && python benchmarks/validation.py
```

Confirms correctness first, then regenerates research artifacts.

## Package Inspection

### Verify the package imports

```bash
python -c "import cores; print(cores.__version__)"
```

Quick import and version sanity check.

### Show installed package metadata

```bash
pip show cores-runtime
```

Displays the installed package version, location, and dependencies.

## Git

### Show working tree status

```bash
git status
```

Shows staged, modified, and untracked files.

### Stage all local changes

```bash
git add .
```

Stages all modified and new files in the repo.

### Commit staged changes

```bash
git commit -m "Short descriptive message"
```

Creates a commit from the current index.

### Push the current branch

```bash
git push
```

Pushes the current branch to its configured remote.
