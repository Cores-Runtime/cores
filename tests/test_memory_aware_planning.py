import pytest
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy
from cores.core.planning.goal_planner import GoalPlanner, ActionModel
from cores.core.planning.policy import LinearInfluencePolicy
from cores.core.planning.memory_aware import MemoryAwarePlanner
from cores.core.memory import Memory, MemoryRecord, MemoryType, MemoryQuery
from cores.core.memory.evidence import EvidenceSet


class TwoCandidateStrategy(PlannerStrategy):
    """Always proposes two candidates; plan_a has higher base utility."""

    def __init__(self, utility_a=0.8, utility_b=0.6):
        self._utility_a = utility_a
        self._utility_b = utility_b

    def plan(self, state, mission, context):
        a = PlanCandidate(
            plan_id="plan_a", goal_id="g1",
            actions=[Action(action_id="act_a", name="open_door_a", cost=1.0)],
            confidence=0.9, utility=self._utility_a,
        )
        b = PlanCandidate(
            plan_id="plan_b", goal_id="g1",
            actions=[Action(action_id="act_b", name="open_door_b", cost=1.0)],
            confidence=0.7, utility=self._utility_b,
        )
        return PlanningResult(
            candidates=[a, b], selected=a,
            metrics=PlanningMetrics(candidates_generated=2, goals_considered=1,
                                    strategy_name=self.name),
        )

    def replan(self, state, mission, context, previous_plan, changes):
        return None

    @property
    def name(self):
        return "two"


def _mission():
    return Mission("m1", goals=[Goal(goal_id="g1", description="enter")])


def _memory_with_failures(action, count) -> Memory:
    mem = Memory()
    for i in range(count):
        mem.store(
            MemoryRecord(
                id=f"out_{i}",
                content={"action": action, "result": "FAILURE"},
                cycle=i + 1,
                importance=0.8,
                record_type=MemoryType.OUTCOME,
            )
        )
    mem.execute(RobotState(), RuntimeContext(cycle_count=0))
    return mem


def _memory_with_success(action, count) -> Memory:
    mem = Memory()
    for i in range(count):
        mem.store(
            MemoryRecord(
                id=f"out_{i}",
                content={"action": action, "result": "SUCCESS"},
                cycle=i + 1,
                importance=0.8,
                record_type=MemoryType.OUTCOME,
            )
        )
    mem.execute(RobotState(), RuntimeContext(cycle_count=0))
    return mem


class TestMemoryAwarePlanner:
    def test_without_memory_matches_base(self):
        planner = MemoryAwarePlanner(TwoCandidateStrategy())
        result = planner.plan(RobotState(), _mission(), PlanningContext())
        assert result.selected.plan_id == "plan_a"
        assert result.metrics.strategy_name == "memory_aware:two"

    def test_name(self):
        planner = MemoryAwarePlanner(TwoCandidateStrategy())
        assert planner.name == "memory_aware:two"

    def test_failure_evidence_flips_selection(self):
        planner = MemoryAwarePlanner(TwoCandidateStrategy())
        mem = _memory_with_failures("open_door_a", 2)
        ctx = PlanningContext(memory=mem)
        result = planner.plan(RobotState(), _mission(), ctx)
        assert result.selected.plan_id == "plan_b"

    def test_success_evidence_can_flip_selection(self):
        planner = MemoryAwarePlanner(
            TwoCandidateStrategy(utility_a=0.44, utility_b=0.40)
        )
        mem = _memory_with_success("open_door_b", 1)
        ctx = PlanningContext(memory=mem)
        result = planner.plan(RobotState(), _mission(), ctx)
        assert result.selected.plan_id == "plan_b"

    def test_evidence_injected_into_context(self):
        planner = MemoryAwarePlanner(TwoCandidateStrategy())
        mem = _memory_with_failures("open_door_a", 1)
        ctx = PlanningContext(memory=mem)
        planner.plan(RobotState(), _mission(), ctx)
        evidence = ctx.metadata["memory_evidence"]
        assert isinstance(evidence, EvidenceSet)
        assert evidence.failure_count("open_door_a") == 1

    def test_stores_plan_record(self):
        planner = MemoryAwarePlanner(TwoCandidateStrategy())
        mem = Memory()
        ctx = PlanningContext(memory=mem)
        planner.plan(RobotState(), _mission(), ctx)
        mem.execute(RobotState(), RuntimeContext(cycle_count=0))
        records = mem.ask(MemoryQuery(memory_types=[MemoryType.PLAN])).records
        assert len(records) == 1
        assert records[0].record_type == MemoryType.PLAN
        assert records[0].content["plan_id"] == "plan_a"

    def test_candidates_kept_in_base_order_on_tie(self):
        planner = MemoryAwarePlanner(
            TwoCandidateStrategy(utility_a=0.5, utility_b=0.5)
        )
        result = planner.plan(RobotState(), _mission(), PlanningContext())
        assert [c.plan_id for c in result.candidates] == ["plan_a", "plan_b"]

    def test_adjusted_candidates_rebuilt_not_mutated(self):
        planner = MemoryAwarePlanner(TwoCandidateStrategy())
        base = TwoCandidateStrategy()
        base_result = base.plan(RobotState(), _mission(), PlanningContext())
        mem = _memory_with_failures("open_door_a", 2)
        ctx = PlanningContext(memory=mem)
        result = planner.plan(RobotState(), _mission(), ctx)
        assert base_result.candidates[0].utility == pytest.approx(0.8)
        plan_a = next(c for c in result.candidates if c.plan_id == "plan_a")
        assert plan_a.utility == pytest.approx(0.5)

    def test_replan_falls_back_to_base_plan(self):
        planner = MemoryAwarePlanner(TwoCandidateStrategy())
        mem = _memory_with_failures("open_door_a", 2)
        ctx = PlanningContext(memory=mem)
        prev = PlanCandidate(plan_id="plan_a", goal_id="g1",
                             actions=[Action(action_id="act_a", name="open_door_a")],
                             utility=0.8, confidence=0.9)
        result = planner.replan(RobotState(), _mission(), ctx, prev, {"objects": []})
        assert result is not None
        assert result.selected.plan_id == "plan_b"

    def test_replan_delegates_to_base_replan(self):
        class ReplanningStrategy(TwoCandidateStrategy):
            def replan(self, state, mission, context, previous_plan, changes):
                b = PlanCandidate(
                    plan_id="plan_b", goal_id="g1",
                    actions=[Action(action_id="act_b", name="open_door_b", cost=1.0)],
                    confidence=0.7, utility=0.6,
                )
                return PlanningResult(
                    candidates=[b], selected=b,
                    metrics=PlanningMetrics(candidates_generated=1, goals_considered=1,
                                            replanning_triggered=True,
                                            strategy_name=self.name),
                )

        planner = MemoryAwarePlanner(ReplanningStrategy())
        ctx = PlanningContext(memory=None)
        prev = PlanCandidate(plan_id="plan_a", goal_id="g1",
                             actions=[Action(action_id="act_a", name="open_door_a")],
                             utility=0.8, confidence=0.9)
        result = planner.replan(RobotState(), _mission(), ctx, prev, {"objects": []})
        assert result.selected.plan_id == "plan_b"
        assert result.metrics.replanning_triggered is True

    def test_wraps_real_goal_planner(self):
        planner = MemoryAwarePlanner(GoalPlanner(actions=[
            ActionModel(action_id="charge", name="charge", cost=1.0,
                        preconditions={"battery": 0.3}, effects={"battery": 1.0}),
        ]))
        mission = Mission("m1", goals=[
            Goal(goal_id="g1", description="charged",
                 constraints={"battery": 1.0}, priority=1.0),
        ])
        state = RobotState(battery_level=0.3)
        ctx = PlanningContext(memory=Memory())
        result = planner.plan(state, mission, ctx)
        assert result.selected is not None
        assert result.selected.actions[0].name == "charge"
        assert result.metrics.strategy_name == "memory_aware:goal"


class TestLinearInfluencePolicy:
    def test_adjust_utility(self):
        policy = LinearInfluencePolicy()
        assert policy.adjust_utility(0.8, failures=2, successes=0) == pytest.approx(0.5)
        assert policy.adjust_utility(0.8, failures=0, successes=1) == pytest.approx(0.85)
        assert policy.adjust_utility(0.05, failures=1, successes=0) == 0.0

    def test_adjust_confidence_clamped(self):
        policy = LinearInfluencePolicy()
        assert policy.adjust_confidence(0.9, failures=100, successes=0) == 0.0
        assert policy.adjust_confidence(0.9, failures=0, successes=100) == 1.0
        assert policy.adjust_confidence(0.5, failures=1, successes=0) == pytest.approx(0.35)

    def test_frozen(self):
        policy = LinearInfluencePolicy()
        with pytest.raises((AttributeError, TypeError)):
            policy.failure_penalty = 0.5
