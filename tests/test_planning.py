import pytest
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy, Planner
from cores.core.robot_state import RobotState
from cores.core.runtime import Runtime


class TestGoal:
    def test_minimal_goal(self):
        g = Goal(goal_id="g1", description="test goal")
        assert g.goal_id == "g1"
        assert g.description == "test goal"
        assert g.priority == 1.0
        assert g.category == "generic"
        assert g.constraints == {}

    def test_goal_with_all_fields(self):
        g = Goal(goal_id="g2", description="explore", priority=0.8,
                 category="exploration", constraints={"max_distance": 100})
        assert g.priority == 0.8
        assert g.category == "exploration"
        assert g.constraints == {"max_distance": 100}

    def test_goal_immutable(self):
        g = Goal(goal_id="g1", description="test")
        with pytest.raises((AttributeError, TypeError)):
            g.priority = 0.5

    def test_goal_equality(self):
        g1 = Goal(goal_id="g1", description="a")
        g2 = Goal(goal_id="g1", description="a")
        assert g1 == g2


class TestAction:
    def test_minimal_action(self):
        a = Action(action_id="a1", name="move_forward")
        assert a.action_id == "a1"
        assert a.name == "move_forward"
        assert a.cost == 1.0
        assert a.duration_cycles == 1
        assert a.preconditions == {}
        assert a.effects == {}

    def test_action_with_effects(self):
        a = Action(action_id="a2", name="pick_up", cost=3.0, duration_cycles=2,
                   preconditions={"arm_free": True}, effects={"holding": True})
        assert a.cost == 3.0
        assert a.duration_cycles == 2
        assert a.preconditions == {"arm_free": True}
        assert a.effects == {"holding": True}

    def test_action_immutable(self):
        a = Action(action_id="a1", name="test")
        with pytest.raises((AttributeError, TypeError)):
            a.cost = 2.0


class TestPlanCandidate:
    def test_minimal_candidate(self):
        actions = [Action(action_id="a1", name="step")]
        p = PlanCandidate(plan_id="p1", goal_id="g1", actions=actions)
        assert p.plan_id == "p1"
        assert p.goal_id == "g1"
        assert p.actions == actions
        assert p.confidence == 1.0

    def test_candidate_with_metrics(self):
        actions = [Action(action_id="a1", name="step", cost=2.0)]
        p = PlanCandidate(plan_id="p1", goal_id="g1", actions=actions,
                          confidence=0.9, estimated_cost=2.0,
                          estimated_duration_cycles=1, utility=0.85)
        assert p.confidence == 0.9
        assert p.estimated_cost == 2.0
        assert p.estimated_duration_cycles == 1
        assert p.utility == 0.85

    def test_candidate_immutable(self):
        p = PlanCandidate(plan_id="p1", goal_id="g1", actions=[])
        with pytest.raises((AttributeError, TypeError)):
            p.confidence = 0.5


class TestPlanningMetrics:
    def test_default_metrics(self):
        m = PlanningMetrics()
        assert m.planning_latency_ms == 0.0
        assert m.candidates_generated == 0
        assert m.goals_considered == 0
        assert m.replanning_triggered is False
        assert m.strategy_name == ""

    def test_custom_metrics(self):
        m = PlanningMetrics(planning_latency_ms=12.5, candidates_generated=3,
                            goals_considered=2, replanning_triggered=True,
                            strategy_name="test")
        assert m.planning_latency_ms == 12.5
        assert m.candidates_generated == 3
        assert m.replanning_triggered is True

    def test_metrics_immutable(self):
        m = PlanningMetrics()
        with pytest.raises((AttributeError, TypeError)):
            m.candidates_generated = 5


class TestPlanningResult:
    def test_empty_candidates(self):
        r = PlanningResult(candidates=[])
        assert r.candidates == []
        assert r.selected is None
        assert r.metrics.candidates_generated == 0

    def test_with_selected_plan(self):
        actions = [Action(action_id="a1", name="step")]
        plan = PlanCandidate(plan_id="p1", goal_id="g1", actions=actions)
        r = PlanningResult(candidates=[plan], selected=plan,
                           metrics=PlanningMetrics(candidates_generated=1))
        assert r.selected == plan
        assert r.metrics.candidates_generated == 1

    def test_result_immutable(self):
        r = PlanningResult(candidates=[])
        with pytest.raises((AttributeError, TypeError)):
            r.candidates = [PlanCandidate(plan_id="x", goal_id="y", actions=[])]


class TestMission:
    def test_minimal_mission(self):
        m = Mission(mission_id="m1", goals=[])
        assert m.mission_id == "m1"
        assert m.goals == []
        assert m.state == "active"
        assert m.priority == 1.0

    def test_mission_with_goals(self):
        goals = [Goal(goal_id="g1", description="explore", priority=0.9)]
        m = Mission(mission_id="m1", goals=goals, state="active", priority=0.8)
        assert len(m.goals) == 1
        assert m.goals[0].description == "explore"
        assert m.state == "active"

    def test_mission_is_mutable(self):
        m = Mission(mission_id="m1", goals=[])
        m.state = "completed"
        assert m.state == "completed"


class TestPlanningContext:
    def test_default_context(self):
        ctx = PlanningContext()
        assert ctx.cycle_count == 0
        assert ctx.compute_budget == 1.0
        assert ctx.time_budget_ms == 100.0
        assert ctx.world_state == {}
        assert ctx.environment_changed is False

    def test_custom_context(self):
        ctx = PlanningContext(cycle_count=5, compute_budget=0.5,
                              time_budget_ms=50.0,
                              world_state={"obstacle_count": 3},
                              environment_changed=True)
        assert ctx.cycle_count == 5
        assert ctx.world_state == {"obstacle_count": 3}
        assert ctx.environment_changed is True

    def test_context_mutable(self):
        ctx = PlanningContext()
        ctx.cycle_count = 10
        ctx.environment_changed = True
        assert ctx.cycle_count == 10
        assert ctx.environment_changed is True


class TestPlannerStrategy:
    def test_abc_cannot_instantiate(self):
        with pytest.raises(TypeError):
            PlannerStrategy()

    def test_abc_enforces_plan(self):
        class Incomplete(PlannerStrategy):
            @property
            def name(self):
                return "incomplete"
        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_strategy(self):
        class TestStrategy(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[],
                                      metrics=PlanningMetrics(strategy_name=self.name))

            @property
            def name(self):
                return "test_strategy"

        strategy = TestStrategy()
        result = strategy.plan(RobotState(), Mission(mission_id="m", goals=[]),
                               PlanningContext())
        assert len(result.candidates) == 0
        assert result.metrics.strategy_name == "test_strategy"

    def test_replan_returns_none_by_default(self):
        class TestStrategy(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[])

            @property
            def name(self):
                return "test"

        strategy = TestStrategy()
        result = strategy.replan(RobotState(), Mission("m", []),
                                 PlanningContext(), None, {})
        assert result is None


class TestPlanner:
    def test_wraps_strategy(self):
        class TestStrategy(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[],
                                      metrics=PlanningMetrics(strategy_name=self.name))

            @property
            def name(self):
                return "wrapped"

        planner = Planner(TestStrategy())
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.metrics.strategy_name == "wrapped"

    def test_strategy_swap(self):
        class StrategyA(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[],
                                      metrics=PlanningMetrics(strategy_name=self.name))
            @property
            def name(self):
                return "A"

        class StrategyB(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[],
                                      metrics=PlanningMetrics(strategy_name=self.name))
            @property
            def name(self):
                return "B"

        planner = Planner(StrategyA())
        assert planner.strategy.name == "A"
        planner.strategy = StrategyB()
        assert planner.strategy.name == "B"
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.metrics.strategy_name == "B"

    def test_replan_delegation(self):
        class TestStrategy(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[])

            def replan(self, state, mission, context, previous_plan, changes):
                return PlanningResult(candidates=[], metrics=PlanningMetrics(strategy_name="replanned"))

            @property
            def name(self):
                return "replan_test"

        planner = Planner(TestStrategy())
        result = planner.replan(RobotState(), Mission("m", []),
                                PlanningContext(), None, {})
        assert result is not None
        assert result.metrics.strategy_name == "replanned"

    def test_strategy_property(self):
        class S(PlannerStrategy):
            def plan(self, *args, **kwargs):
                return PlanningResult(candidates=[])
            @property
            def name(self):
                return "prop_test"

        planner = Planner(S())
        assert isinstance(planner.strategy, PlannerStrategy)


class TestRuntimePlannerIntegration:
    def test_runtime_accepts_planner(self):
        from cores.core.scheduler import Scheduler, DefaultSchedulingPolicy
        from cores.core.execution_layer import ExecutionLayer

        class S(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[])
            @property
            def name(self):
                return "runtime_test"

        planner = Planner(S())
        mission = Mission("test_mission", goals=[
            Goal(goal_id="g1", description="explore", priority=0.8),
        ])
        runtime = Runtime(
            scheduler=Scheduler(DefaultSchedulingPolicy()),
            execution_layer=ExecutionLayer(),
            planner=planner,
            mission=mission,
        )
        assert runtime.planner is planner
        assert runtime.mission.mission_id == "test_mission"
        assert len(runtime.mission.goals) == 1

    def test_runtime_no_planner_defaults(self):
        from cores.core.scheduler import Scheduler, DefaultSchedulingPolicy
        from cores.core.execution_layer import ExecutionLayer

        runtime = Runtime(
            scheduler=Scheduler(DefaultSchedulingPolicy()),
            execution_layer=ExecutionLayer(),
        )
        assert runtime.planner is None
        assert runtime.mission.mission_id == "default"

    def test_planning_runs_in_step_cycle(self):
        from cores.core.scheduler import Scheduler, DefaultSchedulingPolicy
        from cores.core.execution_layer import ExecutionLayer
        from cores.core.state_estimator import SimulatedStateEstimator

        class TestStrategy(PlannerStrategy):
            def __init__(self):
                self.plan_count = 0

            def plan(self, state, mission, context):
                self.plan_count += 1
                return PlanningResult(
                    candidates=[
                        PlanCandidate(
                            plan_id="p1", goal_id="g1",
                            actions=[Action(action_id="a1", name="step")],
                            confidence=0.9,
                        )
                    ],
                    selected=PlanCandidate(
                        plan_id="p1", goal_id="g1",
                        actions=[Action(action_id="a1", name="step")],
                        confidence=0.9,
                    ),
                    metrics=PlanningMetrics(
                        candidates_generated=1, goals_considered=1,
                        strategy_name=self.name,
                    ),
                )

            @property
            def name(self):
                return "step_test"

        strategy = TestStrategy()
        planner = Planner(strategy)
        runtime = Runtime(
            scheduler=Scheduler(DefaultSchedulingPolicy()),
            execution_layer=ExecutionLayer(),
            state_estimator=SimulatedStateEstimator(),
            planner=planner,
        )

        assert strategy.plan_count == 0
        runtime.step()
        assert strategy.plan_count == 1
        runtime.step()
        assert strategy.plan_count == 2

    def test_planning_snapshot_in_runtime_state(self):
        from cores.core.scheduler import Scheduler, DefaultSchedulingPolicy
        from cores.core.execution_layer import ExecutionLayer

        class TestStrategy(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(
                    candidates=[
                        PlanCandidate(
                            plan_id="p1", goal_id="g1",
                            actions=[Action(action_id="a1", name="move")],
                            confidence=0.95, estimated_cost=2.0,
                        )
                    ],
                    selected=PlanCandidate(
                        plan_id="p1", goal_id="g1",
                        actions=[Action(action_id="a1", name="move")],
                        confidence=0.95, estimated_cost=2.0,
                    ),
                    metrics=PlanningMetrics(
                        candidates_generated=1, goals_considered=1,
                        strategy_name=self.name,
                        planning_latency_ms=0.5,
                    ),
                )

            @property
            def name(self):
                return "snapshot_test"

        planner = Planner(TestStrategy())
        runtime = Runtime(
            scheduler=Scheduler(DefaultSchedulingPolicy()),
            execution_layer=ExecutionLayer(),
            planner=planner,
        )
        runtime.step()
        snapshot = runtime.bridge.snapshot()
        assert snapshot is not None
        assert snapshot.planning.strategy == "snapshot_test"
        assert snapshot.planning.candidates_generated == 1
        assert snapshot.planning.selected_plan is not None
        assert snapshot.planning.selected_plan.plan_id == "p1"
        assert snapshot.planning.selected_plan.action_names == ["move"]

    def test_planning_snapshot_no_planner(self):
        from cores.core.scheduler import Scheduler, DefaultSchedulingPolicy
        from cores.core.execution_layer import ExecutionLayer

        runtime = Runtime(
            scheduler=Scheduler(DefaultSchedulingPolicy()),
            execution_layer=ExecutionLayer(),
        )
        runtime.step()
        snapshot = runtime.bridge.snapshot()
        assert snapshot is not None
        assert snapshot.planning.strategy == ""
        assert snapshot.planning.candidates_generated == 0
        assert snapshot.planning.selected_plan is None

    def test_planner_influences_scheduling(self):
        from cores.core.scheduler import (
            Scheduler, CriticalitySchedulingPolicy,
            DefaultCriticalityScoringStrategy, GreedySelectionStrategy,
        )
        from cores.core.execution_layer import ExecutionLayer
        from cores.interfaces.module import Module, ModuleResult, ModuleProfile
        from cores.core.execution_plan import ExecutionPlan

        class PlannerModule(Module):
            def execute(self, state, context):
                return ModuleResult(module_name=self.name)

        class ChargeModule(Module):
            def execute(self, state, context):
                return ModuleResult(module_name=self.name)

        # Register modules with mission_tags that match plan action names
        planner_mod = PlannerModule("planner", priority=5,
            profile=ModuleProfile(
                safety_weight=0.0, mission_weight=0.5, urgency_weight=0.0,
                compute_cost=0.1, time_cost_ms=10, energy_cost=0.1,
                mission_tags=("planning",),
            ))
        charge_mod = ChargeModule("charge_battery", priority=3,
            profile=ModuleProfile(
                safety_weight=0.0, mission_weight=0.3, urgency_weight=0.0,
                compute_cost=0.2, time_cost_ms=20, energy_cost=0.3,
                mission_tags=("charge", "battery"),
            ))

        # Planner produces plan recommending "charge_battery"
        class PlanAwareStrategy(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(
                    candidates=[
                        PlanCandidate(
                            plan_id="p1", goal_id="g1",
                            actions=[Action(action_id="a_charge", name="charge_battery")],
                            confidence=0.9, estimated_cost=1.0,
                        )
                    ],
                    selected=PlanCandidate(
                        plan_id="p1", goal_id="g1",
                        actions=[Action(action_id="a_charge", name="charge_battery")],
                        confidence=0.9, estimated_cost=1.0,
                    ),
                    metrics=PlanningMetrics(
                        candidates_generated=1, goals_considered=1,
                        strategy_name="plan_aware",
                    ),
                )
            @property
            def name(self):
                return "plan_aware"

        policy = CriticalitySchedulingPolicy(
            scoring_strategy=DefaultCriticalityScoringStrategy(),
            selection_strategy=GreedySelectionStrategy(),
        )
        runtime = Runtime(
            scheduler=Scheduler(policy),
            execution_layer=ExecutionLayer(),
            planner=Planner(PlanAwareStrategy()),
        )
        runtime.register_module(planner_mod)
        runtime.register_module(charge_mod)
        runtime.step()

        # The charge_battery module should have a score boost because
        # its mission_tags ("charge", "battery") overlap with the
        # selected plan action name ("charge_battery")
        scores = runtime.context.metrics.get("scores", {})
        assert "charge_battery" in scores, (
            f"charge_battery not scored. modules: "
            f"{[m.name for m in runtime.modules]}, "
            f"scores: {list(scores.keys())}"
        )
        # 1. Planner ran and wrote its result to context
        assert runtime.context.metrics.get("planning_result") is not None
        selected_plan = runtime.context.metrics["planning_result"].selected
        assert selected_plan is not None
        assert selected_plan.actions[0].name == "charge_battery"

        # 2. Scoring strategy read it (plan_boost ran without error)
        plan_boost = policy.scoring_strategy._plan_boost(charge_mod, runtime.context)
        assert plan_boost > 0.0, (
            f"charge_battery module should get plan_boost > 0 from "
            f"mission_tags {{'charge','battery'}} matching action 'charge_battery', "
            f"got {plan_boost}"
        )

        # 3. No boost for modules unrelated to the plan
        plan_boost_unrelated = policy.scoring_strategy._plan_boost(
            planner_mod, runtime.context
        )
        assert plan_boost_unrelated == 0.0, (
            f"unrelated module should get 0 boost, got {plan_boost_unrelated}"
        )
