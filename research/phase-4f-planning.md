# Phase 4F: Mission Planner

## What we're trying to do

State Estimation builds a picture of the world. The Scheduler picks which modules to
run. But nobody's answering "what should we actually be trying to accomplish?"

That's where Planner becomes useful.

It sits between State Estimation and the Scheduler:
- State Estimation says "this is what the world looks like"
- The Planner says "here are some things we could do"
- The Scheduler says "given our resources, here's what we'll actually run"

This is NOT path planning, motion control, SLAM, or ROS navigation. We're not trying
to figure out how to move a robot arm or localize in a map. We're at the cognitive
level: given a mission and a world state, what's a sensible thing to attempt next?

---

## Planning approaches we looked at

### 1. Reactive Planning

Fire rules when conditions are met. If battery < 20%, charge. If obstacle detected,
avoid. No memory of what you planned to do five steps ago.

**Pros:**
- Fast. Like, really fast. O(1) rule lookup.
- Dead simple to write and debug.
- Handles changing environments naturally — there's no plan to invalidate.
- Execution time is predictable.

**Cons:**
- No lookahead. Can't reason about "if I do A now, B will be easier later."
- Multiple goals interacting? Good luck.
- If a rule fires and the action fails, there's no recovery logic — just the next rule.
- Gets messy as you add more rules.

**When you'd use it:** Reflex behaviors, emergency stop, safety guards, game NPCs.

---

### 2. Utility-Based Planning

Score each possible action or goal with a weighted function. Pick the highest score.

**Pros:**
- Weights let you tune behavior without rewriting code.
- Naturally handles trade-offs: "should I charge or keep exploring?"
- Deterministic (same weights + same state = same decision).

**Cons:**
- That utility function is fragile. Bad weights = weird behavior.
- Still no lookahead. You're scoring the current state, not the outcome.
- You need to normalize totally different things (safety vs speed vs battery) onto the
  same scale, which is harder than it sounds.

**When you'd use it:** NPC behavior, resource allocation, any situation with clear
trade-offs between competing goals.

---

### 3. Goal-Oriented Action Planning (GOAP)

Given a goal ("robot is at location B") and a set of actions ("move", "open door"),
search backwards to find a sequence that turns the current state into the goal state.

Originated in the game F.E.A.R. (2005). Still widely used.

**Pros:**
- Plans are generated dynamically, not hand-authored sequences.
- Adding a new action doesn't mean rewriting anything.
- You get cost estimates with each plan.

**Cons:**
- Search space explodes as plans get longer.
- Actions need well-defined preconditions and effects, which is extra work.
- If the world changes, you're replanning from scratch.
- Assumes everything is deterministic (no uncertainty).

**Computational complexity:** O(b^d) worst case. A* heuristics help in practice.

**When you'd use it:** Game AI, task planning in structured environments, any time
you have composable actions.

---

### 4. Behavior Trees

A tree of control nodes (Sequence, Selector, Condition, Action) that gets evaluated
each tick. Originally from games, now used in ROS.

**Pros:**
- Trees are modular. You can reuse subtrees everywhere.
- Easy to read and debug. You can literally draw the tree.
- Naturally hierarchical — high-level behavior at the top, details in subtrees.
- Reactive by design (re-evaluated every tick).

**Cons:**
- Someone has to write the tree. No automated planning — you're encoding strategies.
- Big missions mean big trees. Can get unwieldy.
- No optimality guarantees.
- No learning without bolting on something extra.

**When you'd use it:** Robot control (ROS behavior trees), drone missions, industrial
automation, game AI.

---

### 5. Hierarchical Task Networks (HTN)

Start with a high-level task ("explore the area"). Break it down into subtasks
("navigate to zone A", "scan", "return"). Keep breaking down until you have
primitive actions ("move forward 10cm", "rotate 90 degrees").

**Pros:**
- Hierarchical decomposition is how people naturally think about plans.
- Domain knowledge prunes the search space, so it's fast in practice.
- Can produce partially ordered plans (things that can run in parallel).
- Well-studied, lots of literature.

**Cons:**
- You have to model the whole domain: methods, preconditions, effects. That's a lot
  of upfront work.
- Missing one method can make a perfectly reasonable goal impossible.
- Handling unexpected situations outside your modeled methods is hard.

**When you'd use it:** Manufacturing, military mission planning, game AI with
authored strategies, assembly tasks.

---

### 6. MDPs / POMDPs

Model planning as a math problem: states, actions, transition probabilities,
rewards. Solve for the optimal policy. POMDPs handle not knowing exactly where
you are.

**Pros:**
- Mathematically sound. Optimal policies if you can solve them.
- Handles uncertainty properly.
- Tons of theoretical work to draw from.

**Cons:**
- State space explodes. Adding one sensor dimension doubles it.
- You need explicit transition and reward models, which are hard to write.
- POMDPs are computationally brutal for any realistic problem.
- Encoding rich domain knowledge is awkward.

**When you'd use it:** Small decision problems, resource management, academic
research.

---

### 7. Model Predictive Control (high level)

At each step, solve an optimization problem over a finite horizon. Execute the
first action. Re-solve next step.

**Pros:**
- Handles constraints naturally.
- Optimal over the planning horizon (if the problem is convex).
- Receding horizon means it adapts to changes.

**Cons:**
- You need a good dynamics model.
- Solving an optimization each step isn't free.
- Finite horizon means it can miss long-term strategic goals.
- Usually formulated for continuous control.

**When you'd use it:** Trajectory tracking, drone control, autonomous driving.

---

## What we're actually building

After reading through all of these, here's what made the cut:

1. **ReactivePlanner** — condition-action rules. Baseline. Also serves as safety
   fallback if the fancier planners break.

2. **UtilityPlanner** — weighted scoring. Good default for most situations.
   Simple to tune per deployment.

3. **GoalPlanner** — forward search. Searches through action models to find
   sequences that achieve goals. Picks up where Utility leaves off.

4. **BehaviorTreePlanner** — evaluates a behavior tree and collects the actions
   it would execute. Good for missions with authored strategies.

5. **HTNPlanner** — full hierarchical decomposition. Overkill for simple missions,
   but necessary for complex ones with lots of domain knowledge.

MDP/POMDP and MPC are deferred. MDPs need transition models we don't have yet.
MPC is more useful at the motion control layer, which is a future problem.

---

## How it all fits together

```
Mission
  |
  v
Planner -> Strategy -> PlanningResult
  |             |             |
  |  ReactivePlanner    List<PlanCandidate>
  |  UtilityPlanner          |
  |  GoalPlanner        selected: PlanCandidate
  |  BehaviorTreePlanner     |
  |  HTNPlanner              |
  |                       PlanningMetrics
  |
  v
Scheduler
  |
  v
Execution Layer
```

The Planner wraps a strategy. The Scheduler looks at the candidates when deciding
what to run. Planner just proposes — Scheduler disposes. They stay separate.

All strategies share the same contract:
- Same input (RobotState, Mission, PlanningContext)
- Same output (PlanningResult with a list of candidates)
- Deterministic. Same inputs = same result every time.
- No global state. They're testable in isolation.
