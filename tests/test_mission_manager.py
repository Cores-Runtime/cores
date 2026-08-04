"""Tests for the Mission Manager (Phase 6)."""

import pytest

from cores.core.mission_manager import (
    MissionManager,
    MissionStatus,
    GoalStatus,
    FailureAction,
    GoalConstraintEvaluator,
    MissionSelectionPolicy,
    DefaultMissionFailurePolicy,
    MissionRetryPolicy,
)
from cores.core.mission_manager.policies import (
    DefaultMissionTransitionPolicy,
    MissionTransitionPolicy,
)
from cores.core.planning.mission import Mission
from cores.core.planning.types import Goal
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.planning.interface import Planner, PlannerStrategy
from cores.core.planning.types import Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core import Runtime, Scheduler, DefaultSchedulingPolicy, ExecutionLayer


def _manager(*missions, **kwargs) -> MissionManager:
    return MissionManager(missions=list(missions), **kwargs)


def _state(**kwargs) -> RobotState:
    return RobotState(**kwargs)


def _goal(gid, deps=None, constraints=None) -> Goal:
    constraints = dict(constraints or {})
    if deps is not None:
        constraints["depends_on"] = deps
    return Goal(goal_id=gid, description=gid, constraints=constraints)


# ----------------------------------------------------------------------
# Mission lifecycle
# ----------------------------------------------------------------------


def test_submitted_mission_starts_new_and_not_executable() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    assert manager.status("m1") is MissionStatus.NEW
    assert manager.current_mission() is None
    assert manager.current_goal() is None


def test_execute_promotes_new_to_ready_and_active() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    state = _state()
    manager.execute(state, RuntimeContext())
    assert manager.status("m1") is MissionStatus.ACTIVE
    assert manager.current_mission().mission_id == "m1"
    assert manager.current_goal().goal_id == "g1"
    assert state.mission_status == "active"
    assert state.metadata["mission_id"] == "m1"


def test_new_missions_are_promoted_only_on_execute() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    assert manager.status("m1") is MissionStatus.NEW
    manager.submit(Mission("m2", goals=[_goal("g1")]))
    assert manager.status("m2") is MissionStatus.NEW


def test_duplicate_submit_raises() -> None:
    manager = _manager()
    manager.submit(Mission("m1", goals=[_goal("g1")]))
    with pytest.raises(ValueError):
        manager.submit(Mission("m1", goals=[_goal("g1")]))


def test_unknown_mission_raises() -> None:
    manager = _manager()
    with pytest.raises(KeyError):
        manager.cancel("nope")


def test_mission_with_no_goals_has_no_active_goal() -> None:
    manager = _manager(Mission("m1", goals=[]))
    manager.execute(_state(), RuntimeContext())
    assert manager.current_goal() is None
    assert manager.current_context().is_active is False


def test_completed_mission_surfaces_terminal_state() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    state = _state()
    manager.execute(state, RuntimeContext())
    manager.complete_goal("g1")
    manager.execute(state, RuntimeContext())
    assert state.mission_status == "completed"
    assert state.metadata["mission_id"] == "m1"
    assert state.metadata["progress"] == 1.0


def test_idle_state_when_manager_has_no_missions() -> None:
    manager = MissionManager()
    state = _state()
    manager.execute(state, RuntimeContext())
    assert state.mission_status == "idle"
    assert state.metadata["mission_id"] == ""
    assert state.metadata["progress"] == 0.0


# ----------------------------------------------------------------------
# Goal lifecycle
# ----------------------------------------------------------------------


def test_goal_lifecycle_pending_active_completed() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    record = manager.records()[0]
    assert record.goal_statuses["g1"] is GoalStatus.PENDING
    manager.execute(_state(), RuntimeContext())
    assert record.goal_statuses["g1"] is GoalStatus.ACTIVE
    manager.complete_goal("g1")
    assert record.goal_statuses["g1"] is GoalStatus.COMPLETED


def test_mission_completes_when_all_goals_complete() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1"), _goal("g2")]))
    manager.execute(_state(), RuntimeContext())
    manager.complete_goal("g1")
    assert manager.status("m1") is MissionStatus.ACTIVE
    assert manager.current_goal().goal_id == "g2"
    manager.complete_goal("g2")
    assert manager.status("m1") is MissionStatus.COMPLETED
    assert manager.current_mission() is None


def test_goals_advance_in_order() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1"), _goal("g2"), _goal("g3")]))
    manager.execute(_state(), RuntimeContext())
    assert manager.current_goal().goal_id == "g1"
    manager.complete_goal("g1")
    manager.execute(_state(), RuntimeContext())
    assert manager.current_goal().goal_id == "g2"
    manager.complete_goal("g2")
    manager.execute(_state(), RuntimeContext())
    assert manager.current_goal().goal_id == "g3"


def test_goal_dependencies_block_until_met() -> None:
    manager = _manager(Mission(
        "m1", goals=[_goal("pick"), _goal("drop", deps=["pick"])],
    ))
    manager.execute(_state(), RuntimeContext())
    assert manager.current_goal().goal_id == "pick"
    manager.complete_goal("pick")
    manager.execute(_state(), RuntimeContext())
    assert manager.current_goal().goal_id == "drop"


def test_progress_tracks_completed_goals() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1"), _goal("g2"), _goal("g3")]))
    state = _state()
    manager.execute(state, RuntimeContext())
    assert state.metadata["progress"] == 0.0
    manager.complete_goal("g1")
    manager.execute(state, RuntimeContext())
    assert state.metadata["progress"] == pytest.approx(1 / 3)
    manager.complete_goal("g2")
    manager.execute(state, RuntimeContext())
    assert state.metadata["progress"] == pytest.approx(2 / 3)


# ----------------------------------------------------------------------
# Selection, interruption, pause, resume, cancel
# ----------------------------------------------------------------------


def test_priority_selection_picks_highest() -> None:
    manager = _manager(
        Mission("low", goals=[_goal("g1")], priority=1),
        Mission("high", goals=[_goal("g1")], priority=10),
    )
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission().mission_id == "high"


def test_preemption_returns_current_mission_to_ready() -> None:
    manager = _manager(Mission("low", goals=[_goal("g1")], priority=5))
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission().mission_id == "low"

    manager.submit(Mission("high", goals=[_goal("g1")], priority=10))
    manager.execute(_state(), RuntimeContext())

    assert manager.current_mission().mission_id == "high"
    assert manager.status("low") is MissionStatus.READY


def test_preempted_mission_resumes_when_high_priority_finishes() -> None:
    manager = _manager(Mission("low", goals=[_goal("g1")], priority=5))
    manager.execute(_state(), RuntimeContext())
    manager.submit(Mission("high", goals=[_goal("g1")], priority=10))
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission().mission_id == "high"

    manager.complete_goal("g1")
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission().mission_id == "low"


def test_preempted_mission_retains_progress() -> None:
    manager = _manager(Mission("low", goals=[_goal("g1"), _goal("g2")], priority=5))
    manager.execute(_state(), RuntimeContext())
    manager.complete_goal("g1")
    manager.execute(_state(), RuntimeContext())
    assert manager.current_goal().goal_id == "g2"

    manager.submit(Mission("high", goals=[_goal("g1")], priority=10))
    manager.execute(_state(), RuntimeContext())
    assert manager.status("low") is MissionStatus.READY
    record = next(r for r in manager.records() if r.mission_id == "low")
    assert record.active_goal_index == 1


def test_resume_makes_paused_mission_eligible() -> None:
    manager = _manager(Mission("low", goals=[_goal("g1")], priority=5))
    manager.execute(_state(), RuntimeContext())
    manager.pause("low")
    assert manager.current_mission() is None
    manager.resume("low")
    assert manager.status("low") is MissionStatus.READY
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission().mission_id == "low"


def test_pause_only_applies_to_active_mission() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    manager.pause("m1")
    assert manager.status("m1") is MissionStatus.NEW


def test_cancelled_mission_never_resumes() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    manager.execute(_state(), RuntimeContext())
    manager.cancel("m1")
    assert manager.status("m1") is MissionStatus.CANCELLED
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission() is None


def test_completed_mission_never_resumes() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    manager.execute(_state(), RuntimeContext())
    manager.complete_goal("g1")
    assert manager.status("m1") is MissionStatus.COMPLETED
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission() is None


def test_cancel_new_mission() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    manager.cancel("m1")
    assert manager.status("m1") is MissionStatus.CANCELLED


# ----------------------------------------------------------------------
# Failure and retry policies
# ----------------------------------------------------------------------


def test_failure_retries_then_fails() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    manager.execute(_state(), RuntimeContext())
    manager.fail_goal("g1")
    assert manager.status("m1") is MissionStatus.ACTIVE
    assert manager.records()[0].attempt_counts["g1"] == 1
    manager.fail_goal("g1")
    assert manager.status("m1") is MissionStatus.FAILED


def test_failure_policy_pause_action() -> None:
    class PausePolicy(DefaultMissionFailurePolicy):
        def decide(self, mission_id, goal_id, attempts):
            return FailureAction.PAUSE

    manager = _manager(Mission("m1", goals=[_goal("g1")]), failure_policy=PausePolicy())
    manager.execute(_state(), RuntimeContext())
    manager.fail_goal("g1")
    assert manager.status("m1") is MissionStatus.PAUSED


def test_failure_policy_fail_mission_action() -> None:
    class FailPolicy(DefaultMissionFailurePolicy):
        def decide(self, mission_id, goal_id, attempts):
            return FailureAction.FAIL_MISSION

    manager = _manager(Mission("m1", goals=[_goal("g1")]), failure_policy=FailPolicy())
    manager.execute(_state(), RuntimeContext())
    manager.fail_goal("g1")
    assert manager.status("m1") is MissionStatus.FAILED


def test_failure_policy_cancel_action() -> None:
    class CancelPolicy(DefaultMissionFailurePolicy):
        def decide(self, mission_id, goal_id, attempts):
            return FailureAction.CANCEL_MISSION

    manager = _manager(Mission("m1", goals=[_goal("g1")]), failure_policy=CancelPolicy())
    manager.execute(_state(), RuntimeContext())
    manager.fail_goal("g1")
    assert manager.status("m1") is MissionStatus.CANCELLED


def test_retry_policy_controls_max_attempts() -> None:
    class NoRetry(MissionRetryPolicy):
        def should_retry(self, mission_id, goal_id, attempts):
            return False

    manager = _manager(
        Mission("m1", goals=[_goal("g1")]),
        failure_policy=DefaultMissionFailurePolicy(retry_policy=NoRetry()),
    )
    manager.execute(_state(), RuntimeContext())
    manager.fail_goal("g1")
    assert manager.status("m1") is MissionStatus.FAILED


def test_retried_goal_stays_active() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    manager.execute(_state(), RuntimeContext())
    manager.fail_goal("g1")
    record = manager.records()[0]
    assert record.attempt_counts["g1"] == 1
    assert record.goal_statuses["g1"] is GoalStatus.ACTIVE
    assert manager.current_goal().goal_id == "g1"


# ----------------------------------------------------------------------
# Policies are pluggable
# ----------------------------------------------------------------------


def test_custom_selection_policy() -> None:
    class LastWins(MissionSelectionPolicy):
        def select(self, records):
            return records[-1]

    manager = _manager(
        Mission("first", goals=[_goal("g1")], priority=10),
        Mission("last", goals=[_goal("g1")], priority=1),
        selection_policy=LastWins(),
    )
    manager.execute(_state(), RuntimeContext())
    assert manager.current_mission().mission_id == "last"


def test_transition_policy_blocks_illegal_transition() -> None:
    class BlockActiveToPaused(MissionTransitionPolicy):
        def can_transition(self, source, target):
            return not (source is MissionStatus.ACTIVE and target is MissionStatus.PAUSED)

    manager = _manager(
        Mission("m1", goals=[_goal("g1")]),
        transition_policy=BlockActiveToPaused(),
    )
    manager.execute(_state(), RuntimeContext())
    manager.pause("m1")
    assert manager.status("m1") is MissionStatus.ACTIVE


def test_default_transition_rules() -> None:
    policy = DefaultMissionTransitionPolicy()
    assert not policy.can_transition(MissionStatus.COMPLETED, MissionStatus.ACTIVE)
    assert not policy.can_transition(MissionStatus.CANCELLED, MissionStatus.ACTIVE)
    assert policy.can_transition(MissionStatus.NEW, MissionStatus.READY)
    assert policy.can_transition(MissionStatus.PAUSED, MissionStatus.ACTIVE)
    assert policy.can_transition(MissionStatus.FAILED, MissionStatus.READY)


# ----------------------------------------------------------------------
# Goal completion: explicit API and constraint evaluator are independent
# ----------------------------------------------------------------------


def test_constraint_evaluator_completes_goal_automatically() -> None:
    manager = _manager(
        Mission("m1", goals=[Goal(goal_id="g1", description="deliver",
                                  constraints={"delivered": True})]),
        constraint_evaluator=GoalConstraintEvaluator(),
    )
    state = _state()
    manager.execute(state, RuntimeContext())
    assert manager.current_goal().goal_id == "g1"
    state.metadata["delivered"] = True
    manager.observe_execution([], state)
    assert manager.status("m1") is MissionStatus.COMPLETED


def test_constraint_evaluator_reads_flags() -> None:
    manager = _manager(
        Mission("m1", goals=[Goal(goal_id="g1", description="survey",
                                  constraints={"surveyed": True})]),
        constraint_evaluator=GoalConstraintEvaluator(),
    )
    state = _state()
    manager.execute(state, RuntimeContext())
    state.flags["surveyed"] = True
    manager.observe_execution([], state)
    assert manager.status("m1") is MissionStatus.COMPLETED


def test_no_auto_completion_without_evaluator() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    state = _state()
    manager.execute(state, RuntimeContext())
    state.flags["anything"] = True
    manager.observe_execution([], state)
    assert manager.status("m1") is MissionStatus.ACTIVE
    assert manager.current_goal().goal_id == "g1"


def test_constraint_evaluator_does_not_require_explicit_call() -> None:
    evaluator = GoalConstraintEvaluator()
    state = _state()
    state.metadata["done"] = True
    goal = Goal(goal_id="g1", description="x", constraints={"done": True})
    assert evaluator.is_satisfied(goal, state)


def test_constraint_evaluator_empty_constraints_never_satisfied() -> None:
    evaluator = GoalConstraintEvaluator()
    assert not evaluator.is_satisfied(_goal("g1"), _state())


def test_complete_goal_only_targets_active_goal() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1"), _goal("g2")]))
    manager.execute(_state(), RuntimeContext())
    manager.complete_goal("g2")
    assert manager.status("m1") is MissionStatus.ACTIVE
    assert manager.records()[0].goal_statuses["g2"] is GoalStatus.PENDING


# ----------------------------------------------------------------------
# Runtime integration
# ----------------------------------------------------------------------


class RecordingStrategy(PlannerStrategy):
    def __init__(self):
        self.last_mission = None

    def plan(self, state, mission, context):
        self.last_mission = mission
        goal = mission.goals[0] if mission.goals else None
        plan = PlanCandidate(
            plan_id="p1",
            goal_id=goal.goal_id if goal else "",
            actions=[Action(action_id="a1", name="act1")],
        )
        return PlanningResult(
            candidates=[plan],
            selected=plan,
            metrics=PlanningMetrics(goals_considered=len(mission.goals), strategy_name="record"),
        )

    def replan(self, state, mission, context, previous_plan, changes):
        return None

    @property
    def name(self):
        return "record"


def _runtime(manager: MissionManager, strategy: RecordingStrategy):
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(
        scheduler,
        execution_layer,
        planner=Planner(strategy),
        mission_manager=manager,
    )
    return runtime


def test_runtime_planning_receives_only_active_goal() -> None:
    manager = _manager(Mission(
        "m1", goals=[_goal("g1"), _goal("g2"), _goal("g3")],
    ))
    strategy = RecordingStrategy()
    runtime = _runtime(manager, strategy)

    runtime.step()
    assert strategy.last_mission.mission_id == "m1"
    assert [g.goal_id for g in strategy.last_mission.goals] == ["g1"]

    manager.complete_goal("g1")
    runtime.step()
    assert [g.goal_id for g in strategy.last_mission.goals] == ["g2"]


def test_runtime_mission_state_wiring() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1")]))
    runtime = _runtime(manager, RecordingStrategy())

    runtime.step()
    assert runtime.state.mission_status == "active"
    assert runtime.state.metadata["mission_id"] == "m1"
    assert runtime.state.metadata["progress"] == 0.0

    manager.complete_goal("g1")
    runtime.step()
    assert runtime.state.mission_status == "completed"
    assert runtime.state.metadata["mission_id"] == "m1"
    assert runtime.state.metadata["progress"] == 1.0


def test_runtime_mission_param_backward_compatible() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    mission = Mission("seed", goals=[_goal("g1")])
    runtime = Runtime(scheduler, execution_layer, mission=mission)
    runtime.step()
    assert runtime.state.metadata["mission_id"] == "seed"
    assert runtime.mission == mission


def test_runtime_planning_result_reports_one_goal() -> None:
    manager = _manager(Mission("m1", goals=[_goal("g1"), _goal("g2")]))
    strategy = RecordingStrategy()
    runtime = _runtime(manager, strategy)
    runtime.step()
    result = runtime.context.metrics["planning_result"]
    assert result.metrics.goals_considered == 1
