# CORES Runtime — Command Reference

All commands are run from the `cores/` project root (where `pyproject.toml` lives).

---

## Installation

### Install runtime package (editable)
```bash
pip install -e .
```
Installs `cores-runtime` as an editable package from `src/`.
Any changes to source files are reflected immediately — no reinstall needed.

### Install with dev dependencies
```bash
pip install -e ".[dev]"
```
Installs the runtime plus all development tools: `pytest`, `ruff`, `mypy`.
Run this once after cloning the repo.

---

## Testing

### Run all tests
```bash
python -m pytest
```
Discovers and runs all test files in the `tests/` directory.
Configured via `pyproject.toml` → `[tool.pytest.ini_options]`.

### Run all tests with verbose output
```bash
python -m pytest -v
```
Prints each individual test name and its pass/fail status.
Use this to identify exactly which test failed.

### Run a specific test file
```bash
python -m pytest tests/test_event_bus.py
```
Runs only the tests in the specified file.

### Run a specific test by name
```bash
python -m pytest -k "test_event_bus_routing"
```
Runs only tests whose name matches the given string.

### Run tests and show local variable values on failure
```bash
python -m pytest -l
```
Prints local variable state at the point of failure — useful for debugging.

### Run tests and stop at first failure
```bash
python -m pytest -x
```
Stops the entire test run immediately on the first failing test.

---

## Linting

### Check code style and quality
```bash
python -m ruff check src tests
```
Runs the Ruff linter over `src/` and `tests/`. Reports any rule violations.
Rules are configured via `pyproject.toml` → `[tool.ruff]`.

### Auto-fix fixable lint violations
```bash
python -m ruff check src tests --fix
```
Automatically corrects violations that Ruff can safely fix (e.g., unused imports).
Always review the diff after running this.

### Check a single file
```bash
python -m ruff check src/cores/core/runtime.py
```
Lints only the specified file. Useful for quick pre-commit checks.

---

## Type Checking

### Run static type checker
```bash
python -m mypy src
```
Runs mypy over the entire `src/` directory.
Catches type annotation errors without executing the code.

### Check a single file
```bash
python -m mypy src/cores/core/runtime.py
```
Runs mypy on a specific file.

---

## Full Quality Check (run before every commit)

```bash
python -m ruff check src tests && python -m pytest
```
Lints the entire codebase, then runs the full test suite.
Both must pass before any commit is made.

---

## Git Workflow

### Stage all changes
```bash
git add .
```
Stages every modified and new file in the working directory.

### Commit staged changes
```bash
git commit -m "Short descriptive message"
```
Creates a commit. Message should be imperative, specific, and under 72 characters.

### Push to remote
```bash
git push
```
Pushes the current branch to `origin`.

### Check working tree status
```bash
git status
```
Shows which files are staged, modified, or untracked.

### Untrack a file from git (without deleting it locally)
```bash
git rm -r --cached <path>
```
Removes a file or directory from git's index while keeping it on disk.
Use this when adding a previously committed file/folder to `.gitignore`.

---

## Package Inspection

### List installed package details
```bash
pip show cores-runtime
```
Shows version, location, and dependencies of the installed package.

### Verify the package is importable
```bash
python -c "import cores; print(cores.__version__)"
```
Quick sanity check that the package installs and imports correctly.
