# Mission Manager

## What It Does

The Mission Manager is the layer above Planning. It answers one question:

> Which goal should the robot pursue right now?

Planning keeps answering "how do I achieve a goal?". The Mission Manager
decides which mission and which goal that is. Planning never sees the mission
queue; it receives exactly one active goal per cycle.

## Why It Exists

Before this phase, a mission was handed to the runtime and the planner worked
through its goals in order. Nothing could select, pause, resume, cancel, or
prioritize missions. The robot could not drop a low-value task for an urgent
one, and a finished mission had nowhere to go.

The Mission Manager makes the runtime decide what to work on, not just how.

## Mission Lifecycle

Every mission moves through these states:

```
NEW
 |
 v
READY
 |
 v
ACTIVE
 |  \
 |   v
 |  PAUSED  (retains progress)
 |   |
 |   v
 |  READY  (resume, then selection promotes to ACTIVE)
 v
COMPLETED  or  FAILED  or  CANCELLED
```

Rules:

- NEW: submitted, but not executable yet. Promoted to READY on the next cycle.
- READY: eligible to run. The selection policy picks from READY and ACTIVE.
- ACTIVE: owns the planner. Only the active mission reaches Planning.
- PAUSED: retains progress and the active goal. Only an explicit resume()
  brings it back.
- COMPLETED: all goals done. Never resumes.
- FAILED: may optionally retry (policy driven).
- CANCELLED: never resumes.

A higher-priority mission preempts the active one. The preempted mission
returns to READY, so it runs again the moment the urgent work finishes.

## Goal Lifecycle

Each goal inside a mission runs one at a time:

```
PENDING -> ACTIVE -> COMPLETED  or  FAILED
```

Goals can depend on other goals. A goal whose dependencies are not yet
COMPLETED stays PENDING. Dependencies live in `goal.constraints["depends_on"]`.

## Selecting What Runs

`PriorityMissionSelectionPolicy` activates the highest-priority eligible
mission. This is the default, not the only option. Selection, failure, retry,
and transition behavior all live behind policy abstractions:

- MissionSelectionPolicy
- MissionFailurePolicy
- MissionRetryPolicy
- MissionTransitionPolicy

Behavior belongs in policies. No priorities or retry counts are hardcoded in
the manager.

## Completing a Goal

Two independent mechanisms, either works without the other:

- Explicit API: `complete_goal(goal_id)` or `fail_goal(goal_id)`.
- Optional automatic check: a `GoalConstraintEvaluator` reads
  `goal.constraints` against the current RobotState. A goal with no
  constraints is never auto-completed.

When the active goal fails, the failure policy decides: retry, pause, fail the
mission, or cancel it. A retried goal stays active and is attempted again.

## Runtime Flow

Inside one runtime cycle:

```
Mission Manager executes  ->  picks active mission and active goal
        v
Planning  ->  receives one active goal only
        v
Scheduler
        v
Execution
        v
Mission Manager observes execution results
```

The Mission Manager writes `mission_status`, `mission_id`, and `progress` into
the robot state, so the scheduler scoring and the runtime bridge keep working
without changing them. With no mission ever submitted the state stays `idle`.
Once a mission leaves the active slot, its final state (for example
`completed`, `paused`, or `cancelled`) and progress keep being surfaced until
another mission becomes active, so dashboards can show how the last mission
ended.

## What It Does Not Do

The Mission Manager does not generate plans, execute actions, schedule
modules, estimate state, or store memories.

## Demo

Run it and watch four missions with different priorities interrupt, pause,
resume, and finish:

```bash
cd cores/
uv run python demo_mission_manager.py
```

## Future Extension

Missions today hold a list of goals. A future Mission Graph would let goals
form a graph (Mission -> Goal Graph -> Planning). It is intentionally not
built yet; see side quest #2.
