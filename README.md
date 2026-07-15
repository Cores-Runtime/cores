# CORES

CORES is a deterministic cognitive runtime for embodied systems.

It does not implement robot intelligence directly. It manages which cognitive modules run, in what order, and under what resource constraints.

## Repository Focus

The current repository contains:

- the runtime foundation in `src/cores/`
- unit tests in `tests/`
- microbenchmarks and validation tooling in `benchmarks/`
- research design and discussion documents in `research/`
- project rules and architecture guidance in `AI-Instructions/`

## Current State

Phase 1 runtime infrastructure exists.

Research work for adaptive scheduling is underway through:

- `OperatorSchedulingPolicy` as the fixed-priority baseline
- `EnergyAwarePriorityPolicy` as the resource-aware baseline
- `CriticalitySchedulingPolicy` as the first adaptive policy
- Phase 2A.5 validation artifacts for comparison, sensitivity analysis, and ablation studies
- Phase 2A.6 evaluation framework for rerunning benchmarks under a revised mission-utility definition
- generated scenario suites and Monte Carlo evaluation for broader evidence

## Common Commands

From the `cores/` directory:

```bash
python -m pytest
python benchmarks/run_benchmarks.py
python benchmarks/validation.py
python benchmarks/evaluation_framework.py
```

See [docs/commands.md](docs/commands.md) for the full command reference.

## Key Documents

- [docs/README.md](docs/README.md)
- [AI-Instructions/ARCHITECTURE.md](AI-Instructions/ARCHITECTURE.md)
- [AI-Instructions/ADR/README.md](AI-Instructions/ADR/README.md)
- [research/adaptive_scheduler_design.md](research/adaptive_scheduler_design.md)
- [research/phase_2a5_validation.md](research/phase_2a5_validation.md)
- [research/phase_2a5_discussion.md](research/phase_2a5_discussion.md)
- [research/mission_utility_definition.md](research/mission_utility_definition.md)
- [research/phase_2a6_evaluation_framework.md](research/phase_2a6_evaluation_framework.md)
- [research/phase_2a6_discussion.md](research/phase_2a6_discussion.md)
- [research/experiment_001.md](research/experiment_001.md)

## Project Principle

CORES is intended to be evidence-driven infrastructure.

Scheduler claims should be supported by reproducible tests, benchmarks, and validation artifacts rather than intuition.
