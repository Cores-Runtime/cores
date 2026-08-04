"""Demonstrate the Mission Manager (Phase 6).

Scenario: a facility robot has three missions queued with different
priorities. A higher-priority mission interrupts the current one, the
current mission pauses and retains its progress, a paused mission resumes
when the higher one finishes, and every mission walks its goals from
PENDING to ACTIVE to COMPLETED.

Highlights:
  - Mission lifecycle: NEW -> READY -> ACTIVE -> PAUSED -> ACTIVE -> COMPLETED.
  - Goal lifecycle: PENDING -> ACTIVE -> COMPLETED, one goal at a time.
  - PriorityMissionSelectionPolicy: highest priority owns the planner.
  - Preemption: a higher-priority submission pauses the active mission.
  - Planning always receives one active goal (never the mission queue).
  - Completion uses the explicit API; an optional GoalConstraintEvaluator
    can auto-complete goals from RobotState instead.

Run:  uv run python demo_mission_manager.py
"""

import sys
sys.path.insert(0, "src")

from cores.core.mission_manager import MissionManager, MissionStatus
from cores.core.planning.mission import Mission
from cores.core.planning.types import Goal
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


def heading(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def goals(*ids: str) -> list:
    return [Goal(goal_id=gid, description=gid) for gid in ids]


def status_board(manager: MissionManager, note: str = "") -> None:
    """Print every mission's lifecycle state plus the active goal."""
    rows = []
    for record in manager.records():
        active_goal = (
            record.goal(record.active_goal_index)
            if record.active_goal_index is not None
            else None
        )
        goal_bit = f"  goal={active_goal.goal_id}" if active_goal else ""
        rows.append(f"    {record.mission_id:<10} {record.status.value:<10} "
                    f"progress={record.progress:.2f}{goal_bit}")
    active = manager.current_mission()
    active_id = active.mission_id if active is not None else "(none)"
    suffix = f"  <- {note}" if note else ""
    print(f"  active: {active_id}{suffix}")
    for row in rows:
        print(row)


def main() -> None:
    heading("1. SUBMIT: three missions, three priorities")

    manager = MissionManager()
    manager.submit(Mission("explore", goals=goals("scan_zone_1", "scan_zone_2"), priority=1))
    manager.submit(Mission("patrol", goals=goals("check_gate"), priority=5))
    manager.submit(Mission("deliver", goals=goals("navigate", "drop_off"), priority=10))

    for record in manager.records():
        print(f"    {record.mission_id:<10} status={record.status.value:<10} "
              f"priority={record.mission.priority}")
    print("    (all NEW: submitted but not yet executable)")

    heading("2. FIRST CYCLE: highest priority becomes ACTIVE")

    manager.execute(RobotState(), RuntimeContext())
    status_board(manager, "deliver owns the planner")

    heading("3. PREEMPTION: a higher-priority submission interrupts")

    manager.submit(Mission("rescue", goals=goals("reach_target"), priority=50))
    print("    submitting 'rescue' (priority 50) interrupts 'deliver'.")
    manager.execute(RobotState(), RuntimeContext())
    status_board(manager, "rescue preempted deliver")

    heading("4. PAUSE / RESUME: an explicit pause shelves a mission")

    manager.pause("rescue")
    print("    pause('rescue') -> PAUSED, shelved until resume().")
    manager.execute(RobotState(), RuntimeContext())
    status_board(manager, "deliver (priority 10) takes over while rescue is paused")

    manager.resume("rescue")
    manager.execute(RobotState(), RuntimeContext())
    status_board(manager, "rescue resumed and preempted deliver again")

    heading("5. GOAL LIFECYCLE: rescue walks its goal to COMPLETED")

    rescue = next(r for r in manager.records() if r.mission_id == "rescue")
    print(f"    reach_target: {rescue.goal_statuses['reach_target'].value} -> ACTIVE")
    manager.complete_goal("reach_target")
    print("    complete_goal('reach_target') -> rescue COMPLETED.")
    manager.execute(RobotState(), RuntimeContext())
    status_board(manager, "deliver (priority 10) resumes")

    heading("6. DELIVER: two goals, one at a time, then completion")

    for goal_id in ("navigate", "drop_off"):
        manager.execute(RobotState(), RuntimeContext())
        print(f"    {goal_id}: ACTIVE (current goal)")
        manager.complete_goal(goal_id)
        print(f"    complete_goal('{goal_id}') -> COMPLETED")
    manager.execute(RobotState(), RuntimeContext())
    status_board(manager, "deliver COMPLETED, patrol (priority 5) resumes")

    heading("7. PATROL: completes, then explore gets its turn")

    manager.complete_goal("check_gate")
    print("    complete_goal('check_gate') -> patrol COMPLETED.")
    manager.execute(RobotState(), RuntimeContext())
    status_board(manager, "explore (priority 1) runs last")

    heading("8. EXPLORE: the low-priority mission finishes, robot idles")

    for goal_id in ("scan_zone_1", "scan_zone_2"):
        manager.execute(RobotState(), RuntimeContext())
        manager.complete_goal(goal_id)
    manager.execute(RobotState(), RuntimeContext())
    status_board(manager)

    states = {r.mission_id: r.status for r in manager.records()}
    all_terminal = all(
        s in (MissionStatus.COMPLETED, MissionStatus.CANCELLED, MissionStatus.FAILED)
        for s in states.values()
    )
    print()
    print("  every mission reached a terminal state:", all_terminal)
    print("  final statuses:", ", ".join(f"{k}={v.value}" for k, v in sorted(states.items())))
    print()
    print("  Planning saw exactly one active goal per cycle; the manager never")
    print("  exposed the full mission queue. Completion here used the explicit")
    print("  API. The optional GoalConstraintEvaluator can auto-complete goals")
    print("  from RobotState instead, without the explicit API.")


if __name__ == "__main__":
    main()
