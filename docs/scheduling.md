# Scheduling Policies

CORES currently implements five scheduling policies of increasing sophistication:

| Policy | Approach |
|--------|----------|
| **Default** | Run everything in registration order |
| **Priority** | Fixed priority list, set in advance |
| **Criticality** | Weighted scoring + greedy constraint satisfaction |
| **Knapsack** | 3D DP optimal subset selection |
| **Lexicographic** | Pareto DP with dependency graph awareness |

The Lexicographic scheduler is the most capable of the five - see the [scheduler research design](../research/adaptive_scheduler_design.md) for the full mathematical formulation.

## Execution Cycle

Every call to `Runtime.step()` runs a deterministic pipeline:

1. **State Estimation** → update robot state (battery, pose, flags)
2. **Mission Manager** → pick the active mission and active goal
3. **Memory** → store observations, consolidate, forget
4. **Planning** → plan (or replan) for the single active goal
5. **Events** → flush buffered events from the prior cycle
6. **Schedule** → scheduler produces an ordered execution plan
7. **Execute** → modules run in plan order, return results + events
8. **Mission Manager** → observe execution results (progress, completion)
9. **Publish** → runtime state snapshot published to external consumers
10. **Advance** → cycle count increments

The entire cycle is synchronous, single-threaded, and fully deterministic.
