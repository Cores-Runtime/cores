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

## Key types

- **Planner** -- wraps a strategy. `planner.plan(state, mission, context)`
- **PlannerStrategy** -- what you implement to add a new planner
- **PlanningContext** -- cycle info passed to the planner each step
- **PlanningResult** -- a list of `PlanCandidate` plus timing metrics
- **PlanCandidate** -- an action sequence proposed for a goal
- **Goal** -- something the robot should try to achieve
- **Action** -- a single operation with preconditions and effects
- **Mission** -- a collection of goals

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
| ReactivePlanner | 5/6 | Fails "already_achieved" (can't know what "achieved" means -- it just fires rules) |
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
3. **Run the planner** (if one is configured)
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
| `src/cores/core/planning/goal_planner.py` | GoalPlanner + ActionModel (BFS search) |
| `src/cores/core/planning/behavior_tree_planner.py` | BehaviorTreePlanner + BT node classes |
| `src/cores/core/planning/htn_planner.py` | HTNPlanner + HTNDomain, HTNOperator, HTNMethod |
| `tests/test_planning.py` | Interface + runtime integration tests |
| `tests/test_planning_implementations.py` | Strategy-specific tests (99 tests) |
| `tests/benchmark_planning.py` | Benchmark: all strategies vs all scenarios |
| `research/phase-4f-planning.md` | Deep dive into each planning approach |
| `AI-Instructions/ADR/ADR-011-planning-architecture.md` | Why we built it this way |

## Known limitations

- Planners don't remember what they did last cycle. Each `plan()` call is fresh.
- No probabilistic reasoning yet. MDP/POMDP can be added later via Strategy pattern.
- HTN needs someone to write the domain model (methods, operators, preconditions).
- Behavior Tree is only as good as the tree you give it.
