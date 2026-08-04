from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.world_model.simple_registry import SimpleObjectRegistry
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy, Planner
from cores.core.planning.goal_planner import GoalPlanner, ActionModel
from cores.core.planning.htn_planner import HTNPlanner, HTNDomain, HTNPrimitive, HTNMethod
from cores.core.planning.repair import plan_still_valid, first_blocked_index


def _goal_planner() -> GoalPlanner:
    return GoalPlanner(actions=[
        ActionModel(action_id="approach", name="approach", cost=1.0,
                    preconditions={"at_base": True}, effects={"at_door": True}),
        ActionModel(action_id="open_a", name="open_a", cost=1.0,
                    preconditions={"at_door": True, "door_unlocked": True},
                    effects={"door_open": True}),
        ActionModel(action_id="open_b", name="open_b", cost=1.0,
                    preconditions={"at_door": True, "has_breaker": True},
                    effects={"door_open": True}),
        ActionModel(action_id="enter", name="enter", cost=1.0,
                    preconditions={"door_open": True}, effects={"inside": True}),
    ])


def _mission() -> Mission:
    return Mission("m1", goals=[
        Goal(goal_id="g1", description="get inside",
             constraints={"inside": True}, priority=1.0),
    ])


def _initial_plan(planner: GoalPlanner) -> PlanCandidate:
    state = RobotState(flags={"at_base": True, "door_unlocked": True,
                              "has_breaker": False})
    result = planner.plan(state, _mission(), PlanningContext())
    assert result.selected is not None
    return result.selected


class TestRepairHelpers:
    def test_plan_still_valid_true(self):
        planner = _goal_planner()
        plan = _initial_plan(planner)
        state = RobotState(flags={"at_base": True, "door_unlocked": True,
                                  "has_breaker": False})
        assert plan_still_valid(state, PlanningContext(), plan)

    def test_plan_still_valid_false_when_blocked(self):
        plan = _initial_plan(_goal_planner())
        state = RobotState(flags={"at_base": True, "door_unlocked": False,
                                  "has_breaker": False})
        assert plan_still_valid(state, PlanningContext(), plan) is False

    def test_plan_still_valid_empty_plan(self):
        plan = PlanCandidate(plan_id="p", goal_id="g1", actions=[])
        assert plan_still_valid(RobotState(), PlanningContext(), plan)

    def test_first_blocked_index(self):
        plan = _initial_plan(_goal_planner())
        state = RobotState(flags={"at_base": True, "door_unlocked": False,
                                  "has_breaker": False})
        assert first_blocked_index(state, PlanningContext(), plan) == 1

    def test_progressive_precondition_check(self):
        plan = PlanCandidate(
            plan_id="p", goal_id="g1",
            actions=[
                Action(action_id="a", name="a", preconditions={"at_base": True},
                       effects={"at_door": True}),
                Action(action_id="b", name="b", preconditions={"at_door": True},
                       effects={"inside": True}),
            ],
        )
        state = RobotState(flags={"at_base": True})
        assert plan_still_valid(state, PlanningContext(), plan)


class TestGoalPlannerReplan:
    def test_replan_none_when_valid(self):
        planner = _goal_planner()
        plan = _initial_plan(planner)
        state = RobotState(flags={"at_base": True, "door_unlocked": True,
                                  "has_breaker": False})
        result = planner.replan(state, _mission(), PlanningContext(), plan, {})
        assert result is None

    def test_replan_finds_alternative_entrance(self):
        planner = _goal_planner()
        plan = _initial_plan(planner)
        assert [a.name for a in plan.actions] == ["approach", "open_a", "enter"]

        state = RobotState(flags={"at_base": True, "door_unlocked": False,
                                  "has_breaker": True})
        result = planner.replan(state, _mission(), PlanningContext(), plan, {})
        assert result is not None
        assert result.selected is not None
        names = [a.name for a in result.selected.actions]
        assert names == ["approach", "open_b", "enter"]
        assert result.metrics.replanning_triggered is True
        assert result.context["blocked_index"] == 1

    def test_replan_keeps_valid_prefix(self):
        planner = _goal_planner()
        plan = _initial_plan(planner)
        state = RobotState(flags={"at_base": True, "door_unlocked": False,
                                  "has_breaker": True})
        result = planner.replan(state, _mission(), PlanningContext(), plan, {})
        assert result.selected.actions[0].name == "approach"

    def test_replan_none_when_no_alternative(self):
        planner = GoalPlanner(actions=[
            ActionModel(action_id="approach", name="approach", cost=1.0,
                        preconditions={"at_base": True}, effects={"at_door": True}),
            ActionModel(action_id="open_a", name="open_a", cost=1.0,
                        preconditions={"at_door": True, "door_unlocked": True},
                        effects={"door_open": True}),
            ActionModel(action_id="enter", name="enter", cost=1.0,
                        preconditions={"door_open": True}, effects={"inside": True}),
        ])
        plan = _initial_plan(planner)
        state = RobotState(flags={"at_base": True, "door_unlocked": False,
                                  "has_breaker": False})
        result = planner.replan(state, _mission(), PlanningContext(), plan, {})
        assert result is None

    def test_replan_none_when_goal_missing(self):
        planner = _goal_planner()
        plan = _initial_plan(planner)
        state = RobotState(flags={"at_base": True, "door_unlocked": False,
                                  "has_breaker": True})
        mission = Mission("m2", goals=[Goal(goal_id="other", description="x",
                                            constraints={"inside": True})])
        result = planner.replan(state, mission, PlanningContext(), plan, {})
        assert result is None


class TestHTNReplan:
    def _domain(self) -> HTNDomain:
        domain = HTNDomain()
        domain.add_primitive(HTNPrimitive(name="open_a", cost=1.0,
                                       preconditions={"door_unlocked": True},
                                       effects={"door_open": True}))
        domain.add_primitive(HTNPrimitive(name="open_b", cost=1.0,
                                       preconditions={"has_breaker": True},
                                       effects={"door_open": True}))
        domain.add_primitive(HTNPrimitive(name="enter", cost=1.0,
                                       preconditions={"door_open": True},
                                       effects={"inside": True}))
        domain.add_method(HTNMethod(task="open", subtasks=["open_a"],
                                    condition=lambda s: s.get("door_unlocked", False)))
        domain.add_method(HTNMethod(task="open", subtasks=["open_b"],
                                    condition=lambda s: s.get("has_breaker", False)))
        domain.add_method(HTNMethod(task="enter_room", subtasks=["open", "enter"]))
        return domain

    def _plan(self) -> PlanCandidate:
        planner = HTNPlanner(self._domain())
        state = RobotState(flags={"door_unlocked": True, "has_breaker": False})
        mission = Mission("m1", goals=[
            Goal(goal_id="g1", description="enter", category="enter_room",
                 constraints={"inside": True}, priority=1.0),
        ])
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        return result.selected

    def test_replan_finds_alternative_operator(self):
        planner = HTNPlanner(self._domain())
        plan = self._plan()
        assert [a.name for a in plan.actions] == ["open_a", "enter"]

        state = RobotState(flags={"door_unlocked": False, "has_breaker": True})
        mission = Mission("m1", goals=[
            Goal(goal_id="g1", description="enter", category="enter_room",
                 constraints={"inside": True}, priority=1.0),
        ])
        result = planner.replan(state, mission, PlanningContext(), plan, {})
        assert result is not None
        names = [a.name for a in result.selected.actions]
        assert names == ["open_b", "enter"]
        assert result.metrics.replanning_triggered is True

    def test_replan_none_when_valid(self):
        planner = HTNPlanner(self._domain())
        plan = self._plan()
        state = RobotState(flags={"door_unlocked": True, "has_breaker": False})
        mission = Mission("m1", goals=[
            Goal(goal_id="g1", description="enter", category="enter_room",
                 constraints={"inside": True}, priority=1.0),
        ])
        result = planner.replan(state, mission, PlanningContext(), plan, {})
        assert result is None

    def test_replan_none_when_no_alternative(self):
        domain = HTNDomain()
        domain.add_primitive(HTNPrimitive(name="open_a", cost=1.0,
                                       preconditions={"door_unlocked": True},
                                       effects={"door_open": True}))
        domain.add_primitive(HTNPrimitive(name="enter", cost=1.0,
                                       preconditions={"door_open": True},
                                       effects={"inside": True}))
        domain.add_method(HTNMethod(task="open", subtasks=["open_a"]))
        domain.add_method(HTNMethod(task="enter_room", subtasks=["open", "enter"]))
        planner = HTNPlanner(domain)
        plan = self._plan()  # uses full domain, but blocked open_a is common
        state = RobotState(flags={"door_unlocked": False, "has_breaker": False})
        mission = Mission("m1", goals=[
            Goal(goal_id="g1", description="enter", category="enter_room",
                 constraints={"inside": True}, priority=1.0),
        ])
        # plan_still_valid fails but the minimal domain can't regenerate the tail
        assert plan_still_valid(state, PlanningContext(), plan) is False
        result = planner.replan(state, mission, PlanningContext(), plan, {})
        assert result is None


class TestBaseReplanStaysNone:
    def test_base_strategy_replan_none(self):
        class S(PlannerStrategy):
            def plan(self, state, mission, context):
                return PlanningResult(candidates=[])
            @property
            def name(self):
                return "base"

        assert S().replan(RobotState(), Mission("m", []), PlanningContext(), None, {}) is None


class TestRuntimeReplanOrchestration:
    def _runtime(self, strategy):
        from cores.core.scheduler import Scheduler, DefaultSchedulingPolicy
        from cores.core.execution_layer import ExecutionLayer
        from cores.core.runtime import Runtime

        return Runtime(
            scheduler=Scheduler(DefaultSchedulingPolicy()),
            execution_layer=ExecutionLayer(),
            planner=Planner(strategy),
        )

    class RecordingStrategy(PlannerStrategy):
        def __init__(self):
            self.plan_count = 0
            self.replan_count = 0
            self.last_changes = None
            self.last_replan_changes = None

        def plan(self, state, mission, context):
            self.plan_count += 1
            self.last_changes = context.change_set
            cand = PlanCandidate(
                plan_id="p1", goal_id="g1",
                actions=[Action(action_id="a1", name="step")], confidence=0.9,
            )
            return PlanningResult(
                candidates=[cand], selected=cand,
                metrics=PlanningMetrics(candidates_generated=1, goals_considered=1,
                                        strategy_name=self.name),
            )

        def replan(self, state, mission, context, previous_plan, changes):
            self.replan_count += 1
            self.last_replan_changes = changes
            return None

        @property
        def name(self):
            return "recording"

    def test_replan_fires_on_world_change_once(self):
        strategy = self.RecordingStrategy()
        runtime = self._runtime(strategy)

        runtime.step()
        assert strategy.plan_count == 1

        runtime.world_model.upsert_object(
            object_id="door_a", object_type="obstacle",
            position={"x": 1.0, "y": 2.0}, confidence=0.9, cycle=1,
        )

        runtime.step()  # change is detected at end of this cycle
        runtime.step()  # replan fires here
        runtime.step()  # no further change

        assert strategy.plan_count == 4
        assert strategy.replan_count == 1
        assert "objects" in strategy.last_replan_changes

    def test_no_change_never_replans(self):
        strategy = self.RecordingStrategy()
        runtime = self._runtime(strategy)
        for _ in range(3):
            runtime.step()
        assert strategy.plan_count == 3
        assert strategy.replan_count == 0

    def test_planner_delegates_replan(self):
        class DelegatingStrategy(PlannerStrategy):
            def __init__(self):
                self.replanned = False

            def plan(self, state, mission, context):
                cand = PlanCandidate(
                    plan_id="p1", goal_id="g1",
                    actions=[Action(action_id="a1", name="step")], confidence=0.9,
                )
                return PlanningResult(
                    candidates=[cand], selected=cand,
                    metrics=PlanningMetrics(candidates_generated=1, goals_considered=1,
                                            strategy_name=self.name),
                )

            def replan(self, state, mission, context, previous_plan, changes):
                self.replanned = True
                cand = PlanCandidate(
                    plan_id="p1_repaired", goal_id="g1",
                    actions=[Action(action_id="a1", name="step")], confidence=0.9,
                )
                return PlanningResult(
                    candidates=[cand], selected=cand,
                    metrics=PlanningMetrics(candidates_generated=1, goals_considered=1,
                                            replanning_triggered=True,
                                            strategy_name=self.name),
                )

            @property
            def name(self):
                return "delegating"

        strategy = DelegatingStrategy()
        runtime = self._runtime(strategy)
        runtime.step()
        runtime.world_model.upsert_object(
            object_id="door_a", object_type="obstacle",
            position={"x": 1.0, "y": 2.0}, confidence=0.9, cycle=1,
        )
        runtime.step()
        runtime.step()
        assert strategy.replanned is True
        result = runtime.context.metrics["planning_result"]
        assert result is not None
        assert result.metrics.replanning_triggered is True


class TestStateEstimationChangeSignal:
    def test_change_signal_updates_across_executes(self):
        from cores.core.state_estimation import StateEstimation

        registry = SimpleObjectRegistry()
        se = StateEstimation(strategy=registry)

        se.execute(RobotState(), RuntimeContext(cycle_count=0))
        assert se.last_environment_changed is False
        assert se.last_change_set == {}

        registry.upsert_object(
            object_id="door_a", object_type="obstacle",
            position={"x": 1.0, "y": 2.0}, confidence=0.9, cycle=1,
        )
        se.execute(RobotState(), RuntimeContext(cycle_count=1))
        assert se.last_environment_changed is True
        assert "objects" in se.last_change_set

        se.execute(RobotState(), RuntimeContext(cycle_count=2))
        assert se.last_environment_changed is False
