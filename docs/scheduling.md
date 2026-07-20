# Scheduling Policies

CORES currently implements five scheduling policies of increasing sophistication:

| Policy | Approach |
|--------|----------|
| **Default** | Run everything in registration order |
| **Priority** | Fixed priority (human operator baseline) |
| **Criticality** | Weighted scoring + greedy constraint satisfaction |
| **Knapsack** | 3D DP optimal subset selection |
| **Lexicographic** | Pareto DP with dependency graph awareness |

The Lexicographic scheduler is the current apex - see the [scheduler research design](../research/adaptive_scheduler_design.md) for the full mathematical formulation.

## Execution Cycle

Every call to `Runtime.step()` runs a deterministic pipeline:

1. **State Estimation** → update robot state (battery, pose, flags)
2. **Event Collection** → flush buffered events from the prior cycle
3. **Planning** → scheduler produces an ordered execution plan
4. **Execution** → modules run in plan order, return results + events
5. **Bridge** → runtime state snapshot published to external consumers
6. **Advance** → cycle count increments

The entire cycle is synchronous, single-threaded, and fully deterministic.
