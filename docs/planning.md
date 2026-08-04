# Planning: "What should we do next?"

State Estimation tells you what the world looks like. The Scheduler picks what
modules to run. The Planner sits in between: it looks at your mission and the
current state, and says "here are some things we could try to do."

It doesn't execute anything. It just proposes plans. The scheduler still decides
what actually runs.

```
Mission
  |
  v
StateEstimation
  |
  v
Planner -> [candidate plans]
  |
  v
Scheduler -> Execution Layer
```

## Strategies

| Strategy | How it works | When to use it |
|---|---|---|
| **ReactivePlanner** | Fire rules when conditions are met. Fast, simple. | Emergency fallback, low-latency reflexes |
| **UtilityPlanner** | Score each goal with weighted factors, pick the best. | Default for most missions, trade-off reasoning |
| **GoalPlanner** | Search forward through action models to find plans. | When you need multi-step plans with actions |
| **BehaviorTreePlanner** | Evaluate a behavior tree, collect the actions. | Authored missions, structured control |
| **HTNPlanner** | Break high-level tasks into primitives. | Complex missions with lots of domain knowledge |
| **MemoryAwarePlanner** | Wraps any strategy; biases candidates with memory evidence. | When past failures/successes should steer decisions |

## Key types

- **Planner**: wraps a strategy. `planner.plan(state, mission, context)`
- **PlannerStrategy**: what you implement to add a new planner
- **PlanningContext**: cycle info passed to the planner each step
- **PlanningResult**: a list of `PlanCandidate` plus timing metrics
- **PlanCandidate**: an action sequence proposed for a goal
- **Goal**: something the robot should try to achieve
- **Action**: a single operation with preconditions and effects
- **Mission**: a collection of goals

### Plan repair and replanning

`PlannerStrategy.replan(state, mission, context, previous_plan, changes)` returns
None when the previous plan is still valid, or a new `PlanningResult` when it must
change. `GoalPlanner` and `HTNPlanner` implement prefix-preserving repair: they keep
the actions before the first blocked action and regenerate the tail. The repaired
candidate carries `metadata={"repaired": True, "blocked_index": i}`.

The Runtime triggers replanning automatically in step 4: when StateEstimation
reports an environment change (`last_environment_changed`) and a previous plan
exists, it calls `replan()`; if that returns None, it falls back to a fresh
`plan()`. Otherwise it plans as usual.

### Snapshot determinism

`build_planning_snapshot(robot, world, policy)` projects robot + world into a
canonical planning snapshot and `diff_snapshots(a, b)` reports what changed.
The projection is a **pure function** (no caching, no timestamps) and is
deterministic and order-independent:

- objects sorted by id; flags, payload, sensor-health and dict keys sorted
- no raw battery %, pose, or velocity: battery is bucketed
  (`critical < 0.1 < low < 0.3 < medium < 0.6 < high`), temperature is rounded
- positions rounded, sensor health mapped to `healthy`/`degraded`/`failed`

`PlanningSnapshotPolicy` is a frozen dataclass holding every projection knob, so
the same inputs always produce byte-identical output. StateEstimation calls this
internally each cycle and exposes `last_change_set` / `last_environment_changed`.

### Memory-aware planning

`MemoryAwarePlanner` wraps any `PlannerStrategy`:

- Memory is consulted *before* the base plan via `Memory.evidence()`, which returns
  an `EvidenceSet` (failures, successes, narratives) -- planners never see raw records.
- A `MemoryInfluencePolicy` (default `LinearInfluencePolicy`) adjusts each candidate's
  utility/confidence: -0.15 per failed action, +0.05 per successful action, clamped.
- The selected plan is stored as a `PLAN` record so later cycles can consult it.
- With no memory it reduces to the base planner. `replan()` delegates to the base
  (falling back to `plan()` when the base returns None).

## Benchmark scenarios

The benchmarks (`tests/benchmark_planning.py`) test whether each planner makes the
right decision, not just how fast it runs. Each scenario has a concrete situation
and checks the planner's output makes sense for it.

| Scenario | What it tests |
|---|---|
| battery_critical | Battery at 15%. Planners should suggest charging, not exploring. |
| obstacle_avoidance | Obstacle detected. Planners should respond, not ignore it. |
| feasibility_tradeoff | Two goals: high priority but infeasible vs lower priority but doable. |
| already_achieved | Goal conditions already met. Should return empty plan, not busywork. |
| multi_step_plan | Goal requires move -> scan -> report sequence. GoalPlanner + HTN should find it. |
| empty_mission | No goals. No planner should hallucinate work. |

Current results from those scenarios:

| Strategy | Pass rate | Notes |
|---|---|---|
| ReactivePlanner | 5/6 | Fails "already_achieved" (can't know what "achieved" means; it just fires rules) |
| UtilityPlanner | 3/6 | Can't invent goals not in mission. Needs charge goal to consider charging. |
| GoalPlanner | 4/6 | Searches for whatever goal exists. No obstacle awareness. |
| BehaviorTreePlanner | 2/6 | Tree is hand-authored. Falls over on scenarios the tree author didn't anticipate. |
| HTNPlanner | 4/6 | Same limitation as GoalPlanner on obstacle/goal gaps. |

This is honest: each approach has blind spots. The numbers tell you which gaps
each strategy has, not just "does it return something?"

## Where it runs in the cycle

The Runtime step() runs things in this order:

1. Wire the world model into context
2. Estimate robot state (battery, pose, etc.)
3. **Run the planner** (if one is configured) -- plan, or replan when the
   environment changed since the last cycle
4. Schedule and execute modules
5. Run State Estimation (update world model)
6. Publish state snapshot

The planning result shows up in `RuntimeState.planning` and is also stashed in
`context.metrics["planning_result"]`. The scheduler's `DefaultCriticalityScoringStrategy`
reads this and gives a scoring boost to modules whose `mission_tags` match the selected
plan's action names. So if the planner says "charge_battery", modules tagged with
"charge" or "battery" get a higher score -- planning actually influences what the
scheduler prioritizes.

## File layout

| File | What's in it |
|---|---|
| `src/cores/core/planning/interface.py` | Planner, PlannerStrategy, PlanningContext |
| `src/cores/core/planning/types.py` | Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics |
| `src/cores/core/planning/mission.py` | Mission dataclass |
| `src/cores/core/planning/reactive_planner.py` | ReactivePlanner + ReactiveRule |
| `src/cores/core/planning/utility_planner.py` | UtilityPlanner + UtilityWeights |
| `src/cores/core/planning/goal_planner.py` | GoalPlanner + ActionModel (BFS search), prefix-preserving replan() |
| `src/cores/core/planning/behavior_tree_planner.py` | BehaviorTreePlanner + BT node classes |
| `src/cores/core/planning/htn_planner.py` | HTNPlanner + HTNDomain, HTNPrimitive, HTNMethod, replan() |
| `src/cores/core/planning/state.py` | Shared state helpers: `_extract_state`, `_check_conditions`, `_apply_effects` |
| `src/cores/core/planning/repair.py` | plan_still_valid, first_blocked_index, state_after_actions |
| `src/cores/core/planning/snapshot.py` | PlanningSnapshotPolicy, build_planning_snapshot, diff_snapshots |
| `src/cores/core/planning/policy.py` | MemoryInfluencePolicy, LinearInfluencePolicy |
| `src/cores/core/planning/memory_aware.py` | MemoryAwarePlanner wrapper |
| `tests/test_planning.py` | Interface + runtime integration tests |
| `tests/test_planning_implementations.py` | Strategy-specific tests (99 tests) |
| `tests/test_snapshot.py` | Snapshot determinism + change detection |
| `tests/test_planning_repair.py` | Prefix-preserving replan tests |
| `tests/test_memory_aware_planning.py` | Memory-aware planning + influence policy |
| `tests/benchmark_planning.py` | Benchmark: all strategies vs all scenarios |
| `research/phase-4f-planning.md` | Deep dive into each planning approach |
| `AI-Instructions/ADR/ADR-011-planning-architecture.md` | Why we built it this way |
| `AI-Instructions/ADR/0017-plan-repair-and-memory-aware-planning.md` | Plan repair + memory-aware decisions |

## Known limitations

- Base strategies are stateless: each `plan()` call is fresh. `MemoryAwarePlanner`
  is the opt-in way to carry history across cycles via stored PLAN records.
- Repair heuristics are hand-written, not learned.
- No probabilistic reasoning yet. MDP/POMDP can be added later via Strategy pattern.
- HTN needs someone to write the domain model (methods, primitives, preconditions).
- Behavior Tree is only as good as the tree you give it.
