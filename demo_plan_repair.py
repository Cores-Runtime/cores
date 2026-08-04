"""Demonstrate plan repair and memory-aware planning.

Scenario: a hospital delivery robot must reach a room. Its preferred route
goes through Door A. When the world changes (Door A gets blocked), the
planner repairs the plan by keeping the valid prefix and regenerating the
tail. When memory carries repeated failures for Door A and a success for
Door B, the memory-aware planner prefers Door B from the very first plan.

Highlights:
  - build_planning_snapshot + diff_snapshots: deterministic change detection
    that drives the replan trigger.
  - GoalPlanner.replan(): prefix-preserving plan repair.
  - Memory.evidence() -> EvidenceSet: planners consume evidence, not records.
  - MemoryAwarePlanner + LinearInfluencePolicy: memory shifts the choice.

Run:  uv run python demo_plan_repair.py
"""

import sys
sys.path.insert(0, "src")

from cores.core.memory import Memory, MemoryRecord, MemoryType
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.planning import (
    GoalPlanner,
    ActionModel,
    PlanningContext,
    MemoryAwarePlanner,
    build_planning_snapshot,
    diff_snapshots,
)
from cores.core.planning.mission import Mission
from cores.core.planning.types import Goal
from cores.core.world_model.simple_registry import SimpleObjectRegistry


def heading(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def describe(plan) -> str:
    if plan is None:
        return "(no plan)"
    return " -> ".join(a.name for a in plan.actions)


def state(door_a_clear: bool, door_b_clear: bool) -> RobotState:
    return RobotState(
        battery_level=0.7,
        mission_status="active",
        metadata={
            "region": "corridor_2",
            "waypoint": "wp3",
            "door_a_clear": door_a_clear,
            "door_b_clear": door_b_clear,
        },
    )


def build_dual_route_domain() -> list:
    """Two deliverable goals; Door A is the first route GoalPlanner finds."""
    return [
        ActionModel("go_to_room", "go_to_room", cost=1.0, effects={"at_room": True}),
        ActionModel(
            "open_door_a", "open_door_a", cost=1.0,
            preconditions={"at_room": True, "door_a_clear": True},
            effects={"door_a_open": True},
        ),
        ActionModel(
            "open_door_b", "open_door_b", cost=1.0,
            preconditions={"at_room": True, "door_b_clear": True},
            effects={"door_b_open": True},
        ),
        ActionModel(
            "deliver_a", "deliver_a", cost=1.0,
            preconditions={"door_a_open": True},
            effects={"delivered_a": True},
        ),
        ActionModel(
            "deliver_b", "deliver_b", cost=1.0,
            preconditions={"door_b_open": True},
            effects={"delivered_b": True},
        ),
    ]


def build_repair_domain() -> list:
    """Single delivery goal reachable through either door."""
    return [
        ActionModel("go_to_room", "go_to_room", cost=1.0, effects={"at_room": True}),
        ActionModel(
            "open_door_a", "open_door_a", cost=1.0,
            preconditions={"at_room": True, "door_a_clear": True},
            effects={"door_open": True},
        ),
        ActionModel(
            "open_door_b", "open_door_b", cost=1.0,
            preconditions={"at_room": True, "door_b_clear": True},
            effects={"door_open": True},
        ),
        ActionModel(
            "deliver", "deliver", cost=1.0,
            preconditions={"door_open": True},
            effects={"delivered": True},
        ),
    ]


def build_memory() -> Memory:
    """Memory that has seen Door A fail twice and Door B succeed once."""
    memory = Memory()
    for i in range(2):
        memory.store(MemoryRecord(
            id=f"fail_a_{i}",
            content={"action": "open_door_a", "result": "FAILURE"},
            cycle=i + 1,
            importance=0.9,
            record_type=MemoryType.OUTCOME,
        ))
    memory.store(MemoryRecord(
        id="ok_b_1",
        content={"action": "open_door_b", "result": "SUCCESS"},
        cycle=3,
        importance=0.8,
        record_type=MemoryType.OUTCOME,
    ))
    memory.execute(RobotState(), RuntimeContext(cycle_count=3))
    return memory


def main() -> None:
    # =====================================================================
    # Section 1: Snapshot determinism + change detection
    # =====================================================================
    heading("1. SNAPSHOT: deterministic, canonical change detection")

    world = SimpleObjectRegistry()
    world.upsert_object(
        object_id="door_a", object_type="obstacle",
        position={"x": 1.0, "y": 2.0}, confidence=0.9, cycle=1,
        properties={"label": "door_a", "clear": True},
    )
    world.upsert_object(
        object_id="door_b", object_type="obstacle",
        position={"x": 3.0, "y": 4.0}, confidence=0.9, cycle=1,
        properties={"label": "door_b", "clear": True},
    )

    s1 = build_planning_snapshot(state(True, True), world)
    s2 = build_planning_snapshot(state(True, True), world)
    print(f"  same inputs, same snapshot:      {s1 == s2}")
    print(f"  no continuous battery %/pose/vel: 'battery_bucket'={s1['battery_bucket']!r}")

    world.upsert_object(
        object_id="door_a", object_type="obstacle",
        position={"x": 1.0, "y": 2.0}, confidence=0.9, cycle=2,
        properties={"label": "door_a", "clear": False},
    )
    s3 = build_planning_snapshot(state(False, True), world)
    changes = diff_snapshots(s1, s3)
    print(f"  door A blocked -> diff keys:     {sorted(changes)}")
    print("    (runtime uses this to call planner.replan)")

    # =====================================================================
    # Section 2: Plan repair keeps the valid prefix
    # =====================================================================
    heading("2. PLAN REPAIR: keep prefix, regenerate tail")

    planner = GoalPlanner(build_repair_domain())
    mission = Mission("m_deliver", goals=[
        Goal(goal_id="g_deliver", description="deliver medicine",
             constraints={"delivered": True}, priority=1.0),
    ])

    result = planner.plan(state(True, True), mission, PlanningContext())
    print(f"  initial plan:    {describe(result.selected)}")

    ctx = PlanningContext(
        cycle_count=2,
        environment_changed=True,
        change_set={"objects": "door_a blocked"},
    )
    repaired = planner.replan(
        state(False, True), mission, ctx, result.selected, changes=ctx.change_set,
    )
    print(f"  after door A blocked: replan() -> {describe(repaired.selected)}")
    print(f"    metadata: {repaired.selected.metadata}")

    # =====================================================================
    # Section 3: Evidence aggregation (planners see EvidenceSet, not records)
    # =====================================================================
    heading("3. MEMORY: planners consume evidence, not raw records")

    memory = build_memory()
    evidence = memory.evidence()
    print(f"  failure_count('open_door_a') = {evidence.failure_count('open_door_a')}")
    print(f"  success_count('open_door_b') = {evidence.success_count('open_door_b')}")
    print(f"  failure_count('open_door_b') = {evidence.failure_count('open_door_b')}")

    # =====================================================================
    # Section 4: Memory-aware planning shifts the choice
    # =====================================================================
    heading("4. MEMORY-AWARE PLANNING: evidence shifts the selected route")

    base = GoalPlanner(build_dual_route_domain())
    dual = Mission("m_route", goals=[
        Goal(goal_id="g_a", description="deliver via Door A",
             constraints={"delivered_a": True}, priority=1.0),
        Goal(goal_id="g_b", description="deliver via Door B",
             constraints={"delivered_b": True}, priority=1.0),
    ])

    blind = base.plan(state(True, True), dual, PlanningContext())
    print(f"  no memory:   selected {blind.selected.plan_id}  "
          f"({describe(blind.selected)})")

    aware = MemoryAwarePlanner(base, memory=memory)
    biased = aware.plan(state(True, True), dual, PlanningContext(memory=memory))
    print(f"  with memory: selected {biased.selected.plan_id}  "
          f"({describe(biased.selected)})")

    for cand in biased.candidates:
        print(f"    - {cand.plan_id}: utility={cand.utility:.3f}  "
              f"({[a.name for a in cand.actions]})")

    print()
    print("  LinearInfluencePolicy: each failed action -0.15 utility,"
          " each successful action +0.05.")
    print("  Base utility = priority / (1 + cost) = 1 / 4 = 0.25")
    print("  Door A: 0.25 - 2*0.15 = -0.05 -> clamped 0.000")
    print("  Door B: 0.25 + 1*0.05 = 0.300")


if __name__ == "__main__":
    main()
