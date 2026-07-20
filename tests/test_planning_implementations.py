import pytest
from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal, Action
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext
from cores.core.planning.reactive_planner import ReactivePlanner, ReactiveRule
from cores.core.planning.utility_planner import UtilityPlanner, UtilityWeights
from cores.core.planning.goal_planner import GoalPlanner, ActionModel
from cores.core.planning.behavior_tree_planner import (
    BehaviorTreePlanner, BTAction, BTCondition, BTSequence, BTSelector, BTInverter,
)
from cores.core.planning.htn_planner import HTNPlanner, HTNDomain, HTNOperator, HTNMethod


# ---------------------------------------------------------------------------
# ReactivePlanner tests
# ---------------------------------------------------------------------------

class TestReactivePlanner:
    def test_empty_rules(self):
        planner = ReactivePlanner([])
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.candidates == []
        assert result.selected is None
        assert result.metrics.candidates_generated == 0

    def test_no_rules_by_default(self):
        planner = ReactivePlanner()
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.candidates == []

    def test_single_matching_rule(self):
        goal = Goal(goal_id="g1", description="charge")
        action = Action(action_id="a1", name="charge_battery")
        rule = ReactiveRule(
            condition=lambda s, m, c: s.battery_level < 0.5,
            goal=goal, action=action, priority=0,
        )
        planner = ReactivePlanner([rule])
        state = RobotState(battery_level=0.3)
        result = planner.plan(state, Mission("m", []), PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "g1"
        assert result.selected.actions == [action]
        assert result.metrics.candidates_generated == 1

    def test_no_matching_rule(self):
        goal = Goal(goal_id="g1", description="charge")
        action = Action(action_id="a1", name="charge_battery")
        rule = ReactiveRule(
            condition=lambda s, m, c: s.battery_level < 0.2,
            goal=goal, action=action, priority=0,
        )
        planner = ReactivePlanner([rule])
        state = RobotState(battery_level=0.8)
        result = planner.plan(state, Mission("m", []), PlanningContext())
        assert result.selected is None
        assert result.candidates == []

    def test_priority_ordering(self):
        low = ReactiveRule(
            condition=lambda s, m, c: True,
            goal=Goal(goal_id="low", description="low"),
            action=Action(action_id="a1", name="low_priority"),
            priority=0,
        )
        high = ReactiveRule(
            condition=lambda s, m, c: True,
            goal=Goal(goal_id="high", description="high"),
            action=Action(action_id="a2", name="high_priority"),
            priority=10,
        )
        planner = ReactivePlanner([low, high])
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "high"

    def test_rule_condition_with_mission(self):
        goal = Goal(goal_id="g1", description="mission_task")
        action = Action(action_id="a1", name="do_task")
        rule = ReactiveRule(
            condition=lambda s, m, c: m.state == "active" and len(m.goals) > 0,
            goal=goal, action=action, priority=0,
        )
        planner = ReactivePlanner([rule])
        mission = Mission("m1", goals=[goal], state="active")
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None

        mission.state = "paused"
        result2 = planner.plan(RobotState(), mission, PlanningContext())
        assert result2.selected is None

    def test_add_rule_dynamically(self):
        planner = ReactivePlanner()
        assert len(planner.rules) == 0
        rule = ReactiveRule(
            condition=lambda s, m, c: True,
            goal=Goal(goal_id="g", description="g"),
            action=Action(action_id="a", name="a"),
        )
        planner.add_rule(rule)
        assert len(planner.rules) == 1
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.selected is not None

    def test_add_rules_bulk(self):
        planner = ReactivePlanner()
        rules = [
            ReactiveRule(condition=lambda s, m, c: True,
                         goal=Goal(goal_id=f"g{i}", description=f"g{i}"),
                         action=Action(action_id=f"a{i}", name=f"a{i}"))
            for i in range(3)
        ]
        planner.add_rules(rules)
        assert len(planner.rules) == 3

    def test_clear_rules(self):
        rule = ReactiveRule(
            condition=lambda s, m, c: True,
            goal=Goal(goal_id="g", description="g"),
            action=Action(action_id="a", name="a"),
        )
        planner = ReactivePlanner([rule])
        assert len(planner.rules) == 1
        planner.clear_rules()
        assert len(planner.rules) == 0

    def test_rules_immutable_copy(self):
        rule = ReactiveRule(
            condition=lambda s, m, c: True,
            goal=Goal(goal_id="g", description="g"),
            action=Action(action_id="a", name="a"),
        )
        planner = ReactivePlanner([rule])
        rules_copy = planner.rules
        rules_copy.clear()
        assert len(planner.rules) == 1  # internal list unchanged

    def test_condition_uses_context(self):
        goal = Goal(goal_id="g1", description="react")
        action = Action(action_id="a1", name="react")
        rule = ReactiveRule(
            condition=lambda s, m, c: c.environment_changed,
            goal=goal, action=action,
        )
        planner = ReactivePlanner([rule])
        ctx = PlanningContext(environment_changed=True)
        result = planner.plan(RobotState(), Mission("m", []), ctx)
        assert result.selected is not None

        ctx2 = PlanningContext(environment_changed=False)
        result2 = planner.plan(RobotState(), Mission("m", []), ctx2)
        assert result2.selected is None

    def test_exception_in_condition_skips_rule(self):
        goal = Goal(goal_id="g1", description="broken")
        action = Action(action_id="a1", name="broken")
        broken = ReactiveRule(
            condition=lambda s, m, c: (_ for _ in ()).throw(RuntimeError("fail")),
            goal=goal, action=action, priority=0,
        )
        ok = ReactiveRule(
            condition=lambda s, m, c: True,
            goal=Goal(goal_id="g2", description="ok"),
            action=Action(action_id="a2", name="ok"), priority=1,
        )
        planner = ReactivePlanner([broken, ok])
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "g2"

    def test_name(self):
        planner = ReactivePlanner()
        assert planner.name == "reactive"

    def test_metrics_populated(self):
        goal = Goal(goal_id="g1", description="test")
        action = Action(action_id="a1", name="test")
        rule = ReactiveRule(condition=lambda s, m, c: True, goal=goal, action=action)
        planner = ReactivePlanner([rule])
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.metrics.strategy_name == "reactive"
        assert result.metrics.candidates_generated == 1
        assert result.metrics.goals_considered >= 1
        assert result.metrics.planning_latency_ms >= 0

    def test_multiple_rules_all_match_highest_priority_wins(self):
        rules = []
        for i in range(5):
            rules.append(ReactiveRule(
                condition=lambda s, m, c, i=i: True,
                goal=Goal(goal_id=f"g{i}", description=f"g{i}"),
                action=Action(action_id=f"a{i}", name=f"a{i}"),
                priority=i,
            ))
        planner = ReactivePlanner(rules)
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "g4"  # highest priority


# ---------------------------------------------------------------------------
# UtilityPlanner tests
# ---------------------------------------------------------------------------

class TestUtilityPlanner:
    def test_no_goals(self):
        planner = UtilityPlanner()
        result = planner.plan(RobotState(), Mission("m", []), PlanningContext())
        assert result.candidates == []
        assert result.selected is None
        assert result.metrics.candidates_generated == 0

    def test_single_goal(self):
        planner = UtilityPlanner()
        goal = Goal(goal_id="g1", description="explore", priority=1.0)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "g1"
        assert result.metrics.candidates_generated == 1

    def test_multiple_goals_highest_utility_wins(self):
        planner = UtilityPlanner()
        low = Goal(goal_id="low", description="low", priority=0.1)
        high = Goal(goal_id="high", description="high", priority=0.9)
        mission = Mission("m1", goals=[low, high])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "high"

    def test_custom_weights(self):
        weights = UtilityWeights(goal_priority=1.0, feasibility=0.0,
                                  urgency=0.0, efficiency=0.0)
        planner = UtilityPlanner(weights=weights)
        low = Goal(goal_id="low", description="low", priority=0.1)
        high = Goal(goal_id="high", description="high", priority=0.9)
        mission = Mission("m1", goals=[low, high])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "high"

    def test_infeasible_goal_zero_feasibility(self):
        weights = UtilityWeights(goal_priority=0.0, feasibility=1.0,
                                  urgency=0.0, efficiency=0.0)
        planner = UtilityPlanner(weights=weights)
        feasible = Goal(goal_id="ok", description="ok", priority=0.5)
        infeasible = Goal(goal_id="bad", description="bad", priority=0.5,
                          constraints={"max_battery": 0.5})
        mission = Mission("m1", goals=[feasible, infeasible])
        state = RobotState(battery_level=0.3)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "ok"

    def test_infeasible_require_flag(self):
        weights = UtilityWeights(goal_priority=0.0, feasibility=1.0,
                                  urgency=0.0, efficiency=0.0)
        planner = UtilityPlanner(weights=weights)
        feasible = Goal(goal_id="ok", description="ok", priority=0.5)
        infeasible = Goal(goal_id="bad", description="bad", priority=0.5,
                          constraints={"require_flag": "sensor_ready"})
        mission = Mission("m1", goals=[feasible, infeasible])
        state = RobotState(flags={"sensor_ready": False})
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.goal_id == "ok"

    def test_goal_with_deadline_urgency(self):
        weights = UtilityWeights(goal_priority=0.0, feasibility=0.0,
                                  urgency=1.0, efficiency=0.0)
        planner = UtilityPlanner(weights=weights)
        urgent = Goal(goal_id="urgent", description="urgent", priority=0.5,
                      constraints={"deadline_cycles": 5})
        mission = Mission("m1", goals=[urgent])
        ctx = PlanningContext(cycle_count=4)  # close to deadline
        result = planner.plan(RobotState(), mission, ctx)
        assert result.selected is not None
        assert result.metrics.candidates_generated == 1

    def test_registered_action_template(self):
        planner = UtilityPlanner()
        template = Action(action_id="scan", name="perform_scan",
                          cost=2.0, duration_cycles=3)
        planner.register_action("exploration", template)
        goal = Goal(goal_id="g1", description="explore", priority=0.8,
                    category="exploration")
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.actions[0].name == "perform_scan"
        assert result.selected.actions[0].cost == 2.0

    def test_no_template_uses_default_action(self):
        planner = UtilityPlanner()
        goal = Goal(goal_id="g1", description="custom", category="unknown")
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert "unknown" in result.selected.actions[0].name

    def test_multiple_candidates_generated(self):
        planner = UtilityPlanner()
        goals = [Goal(goal_id=f"g{i}", description=f"g{i}",
                      priority=0.1 * (i + 1)) for i in range(5)]
        mission = Mission("m1", goals=goals)
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert len(result.candidates) == 5
        assert result.metrics.candidates_generated == 5

    def test_candidates_sorted_by_utility(self):
        planner = UtilityPlanner()
        g1 = Goal(goal_id="g1", description="low", priority=0.1)
        g2 = Goal(goal_id="g2", description="high", priority=0.9)
        mission = Mission("m1", goals=[g1, g2])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert len(result.candidates) == 2
        assert result.candidates[0].goal_id == "g2"
        assert result.candidates[1].goal_id == "g1"

    def test_confidence_matches_utility(self):
        planner = UtilityPlanner(weights=UtilityWeights(
            goal_priority=1.0, feasibility=0.0, urgency=0.0, efficiency=0.0))
        goal = Goal(goal_id="g1", description="test", priority=0.75)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.confidence == pytest.approx(0.75)

    def test_weights_property(self):
        w = UtilityWeights(goal_priority=0.5, feasibility=0.3,
                            urgency=0.1, efficiency=0.1)
        planner = UtilityPlanner(weights=w)
        assert planner.weights.goal_priority == 0.5
        assert planner.weights.feasibility == 0.3

    def test_name(self):
        planner = UtilityPlanner()
        assert planner.name == "utility"

    def test_metrics(self):
        goal = Goal(goal_id="g1", description="test", priority=0.5)
        mission = Mission("m1", goals=[goal])
        planner = UtilityPlanner()
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.metrics.strategy_name == "utility"
        assert result.metrics.candidates_generated == 1
        assert result.metrics.goals_considered == 1
        assert result.metrics.planning_latency_ms >= 0

    def test_always_deterministic(self):
        planner = UtilityPlanner()
        goals = [Goal(goal_id=f"g{i}", description=f"g{i}",
                      priority=0.5) for i in range(3)]
        mission = Mission("m1", goals=goals)
        r1 = planner.plan(RobotState(), mission, PlanningContext())
        r2 = planner.plan(RobotState(), mission, PlanningContext())
        assert [c.goal_id for c in r1.candidates] == [c.goal_id for c in r2.candidates]


# ---------------------------------------------------------------------------
# GoalPlanner tests
# ---------------------------------------------------------------------------

class TestGoalPlanner:
    def test_no_actions(self):
        planner = GoalPlanner(actions=[])
        goal = Goal(goal_id="g1", description="test", constraints={"battery": 0.5})
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(battery_level=0.5), mission, PlanningContext())
        assert result.selected is not None  # already satisfied, empty plan

    def test_no_goals(self):
        planner = GoalPlanner(actions=[])
        result = planner.plan(RobotState(), Mission("m1", []), PlanningContext())
        assert result.candidates == []
        assert result.selected is None

    def test_simple_forward_search(self):
        actions = [
            ActionModel(action_id="charge", name="charge", cost=1.0,
                        preconditions={"battery": 0.3},
                        effects={"battery": 1.0}),
        ]
        planner = GoalPlanner(actions=actions)
        goal = Goal(goal_id="g1", description="charged",
                    constraints={"battery": 1.0})
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.3)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert len(result.selected.actions) == 1
        assert result.selected.actions[0].name == "charge"

    def test_already_satisfied(self):
        planner = GoalPlanner(actions=[])
        goal = Goal(goal_id="g1", description="done",
                    constraints={"battery": 0.8})
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.8)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.actions == []

    def test_unreachable_goal(self):
        actions = [
            ActionModel(action_id="charge", name="charge", cost=1.0,
                        preconditions={"battery": 0.3},
                        effects={"battery": 1.0}),
        ]
        planner = GoalPlanner(actions=actions, max_depth=5)
        goal = Goal(goal_id="g1", description="charged",
                    constraints={"battery": 0.5})
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.1)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is None  # no action has precondition {battery: 0.1}

    def test_multi_step_plan(self):
        actions = [
            ActionModel(action_id="approach", name="approach", cost=2.0,
                        preconditions={"at_base": True},
                        effects={"at_target": True}),
            ActionModel(action_id="scan", name="scan", cost=1.0,
                        preconditions={"at_target": True},
                        effects={"scanned": True}),
        ]
        planner = GoalPlanner(actions=actions)
        goal = Goal(goal_id="g1", description="scanned",
                    constraints={"scanned": True})
        mission = Mission("m1", goals=[goal])
        state = RobotState(flags={"at_base": True})
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert len(result.selected.actions) == 2
        assert result.selected.actions[0].name == "approach"
        assert result.selected.actions[1].name == "scan"

    def test_add_action_dynamically(self):
        planner = GoalPlanner()
        planner.add_action(ActionModel(action_id="test", name="test", cost=1.0,
                                        preconditions={}, effects={"done": True}))
        goal = Goal(goal_id="g1", description="test", constraints={"done": True})
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None

    def test_metric_goal_conditions_from_constraints(self):
        actions = [
            ActionModel(action_id="move", name="move", cost=1.0,
                        preconditions={"battery": 0.5},
                        effects={"battery": 0.5, "at_location": "zone_a"}),
        ]
        planner = GoalPlanner(actions=actions)
        goal = Goal(goal_id="g1", description="reach_zone",
                    constraints={"at_location": "zone_a"})
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.5)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None

    def test_max_depth_prevents_infinite_loops(self):
        actions = [
            ActionModel(action_id="loop", name="loop", cost=1.0,
                        preconditions={}, effects={"x": 0}),
        ]
        planner = GoalPlanner(actions=actions, max_depth=3)
        goal = Goal(goal_id="g1", description="impossible",
                    constraints={"x": 1})
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is None

    def test_multiple_goals_candidates_sorted(self):
        actions = [
            ActionModel(action_id="do_a", name="do_a", cost=1.0,
                        preconditions={}, effects={"a_done": True}),
            ActionModel(action_id="do_b", name="do_b", cost=1.0,
                        preconditions={}, effects={"b_done": True}),
        ]
        planner = GoalPlanner(actions=actions)
        g_low = Goal(goal_id="g_low", description="low", priority=0.1,
                      constraints={"a_done": True})
        g_high = Goal(goal_id="g_high", description="high", priority=0.9,
                       constraints={"b_done": True})
        mission = Mission("m1", goals=[g_low, g_high])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert len(result.candidates) == 2
        assert result.candidates[0].goal_id == "g_high"

    def test_name(self):
        planner = GoalPlanner(actions=[])
        assert planner.name == "goal"

    def test_metrics(self):
        planner = GoalPlanner(actions=[])
        goal = Goal(goal_id="g1", description="test", constraints={"x": 1})
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.metrics.strategy_name == "goal"
        assert result.metrics.planning_latency_ms >= 0


# ---------------------------------------------------------------------------
# BehaviorTreePlanner tests
# ---------------------------------------------------------------------------

class TestBehaviorTreePlanner:
    def test_single_action_success(self):
        goal = Goal(goal_id="g1", description="move")
        action = Action(action_id="a1", name="move_forward", cost=1.0)
        root = BTAction(action)
        planner = BehaviorTreePlanner(root=root, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert len(result.selected.actions) == 1
        assert result.selected.actions[0].name == "move_forward"

    def test_action_with_failing_condition(self):
        goal = Goal(goal_id="g1", description="scan")
        action = Action(action_id="a1", name="scan")
        root = BTAction(action, condition=lambda s, m, c: s.battery_level > 0.5)
        planner = BehaviorTreePlanner(root=root, goal=goal)
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.3)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is None

    def test_action_with_passing_condition(self):
        goal = Goal(goal_id="g1", description="scan")
        action = Action(action_id="a1", name="scan")
        root = BTAction(action, condition=lambda s, m, c: s.battery_level > 0.3)
        planner = BehaviorTreePlanner(root=root, goal=goal)
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.5)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None

    def test_sequence_all_succeed(self):
        goal = Goal(goal_id="g1", description="process")
        a1 = Action(action_id="a1", name="step1")
        a2 = Action(action_id="a2", name="step2")
        seq = BTSequence(children=[BTAction(a1), BTAction(a2)])
        planner = BehaviorTreePlanner(root=seq, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert len(result.selected.actions) == 2

    def test_sequence_fails_at_first(self):
        goal = Goal(goal_id="g1", description="process")
        a1 = Action(action_id="a1", name="step1")
        fail = BTAction(Action("f", "fail"),
                        condition=lambda s, m, c: False)
        a2 = Action(action_id="a2", name="step2")
        seq = BTSequence(children=[fail, BTAction(a2)])
        planner = BehaviorTreePlanner(root=seq, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is None

    def test_selector_takes_first_success(self):
        goal = Goal(goal_id="g1", description="pick")
        fail = BTAction(Action("f", "fail"),
                        condition=lambda s, m, c: False)
        success = BTAction(Action("a1", "do_it"))
        sel = BTSelector(children=[fail, success])
        planner = BehaviorTreePlanner(root=sel, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.actions[0].name == "do_it"

    def test_selector_all_fail(self):
        goal = Goal(goal_id="g1", description="pick")
        fail1 = BTAction(Action("f1", "fail1"),
                         condition=lambda s, m, c: False)
        fail2 = BTAction(Action("f2", "fail2"),
                         condition=lambda s, m, c: False)
        sel = BTSelector(children=[fail1, fail2])
        planner = BehaviorTreePlanner(root=sel, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is None

    def test_condition_node(self):
        goal = Goal(goal_id="g1", description="check")
        cond = BTCondition(predicate=lambda s, m, c: s.battery_level > 0.5)
        planner = BehaviorTreePlanner(root=cond, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(battery_level=0.8), mission, PlanningContext())
        assert result.selected is None  # condition has no actions
        assert result.metrics.candidates_generated == 0

    def test_inverter_node(self):
        goal = Goal(goal_id="g1", description="invert")
        cond = BTCondition(predicate=lambda s, m, c: False)
        inv = BTInverter(cond)
        action = BTAction(Action("a1", "run"))
        seq = BTSequence(children=[inv, action])
        planner = BehaviorTreePlanner(root=seq, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.actions[0].name == "run"

    def test_goal_not_in_mission(self):
        goal = Goal(goal_id="g1", description="task")
        root = BTAction(Action("a1", "do"))
        planner = BehaviorTreePlanner(root=root, goal=goal)
        other_goal = Goal(goal_id="g2", description="other")
        mission = Mission("m1", goals=[other_goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is None

    def test_bt_decorator_chaining(self):
        goal = Goal(goal_id="g1", description="complex")
        fail_cond = BTCondition(predicate=lambda s, m, c: False)
        a = BTAction(Action("a1", "go"))
        sel = BTSelector(children=[BTSequence(children=[fail_cond]), BTSequence(children=[BTInverter(fail_cond), a])])
        planner = BehaviorTreePlanner(root=sel, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.actions[0].name == "go"

    def test_name(self):
        goal = Goal(goal_id="g1", description="test")
        planner = BehaviorTreePlanner(root=BTAction(Action("a", "a")), goal=goal)
        assert planner.name == "behavior_tree"

    def test_metrics(self):
        goal = Goal(goal_id="g1", description="test")
        root = BTAction(Action("a1", "do"))
        planner = BehaviorTreePlanner(root=root, goal=goal)
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.metrics.strategy_name == "behavior_tree"
        assert result.metrics.planning_latency_ms >= 0


# ---------------------------------------------------------------------------
# HTNPlanner tests
# ---------------------------------------------------------------------------

class TestHTNPlanner:
    def test_no_goals(self):
        domain = HTNDomain()
        planner = HTNPlanner(domain)
        result = planner.plan(RobotState(), Mission("m1", []), PlanningContext())
        assert result.candidates == []
        assert result.selected is None

    def test_primitive_task(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="charge", cost=1.0,
                                        preconditions={"battery": 0.3},
                                        effects={"battery": 1.0}))
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="charge",
                    constraints={"battery": 1.0},
                    category="charge")
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.3)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert len(result.selected.actions) == 1
        assert result.selected.actions[0].name == "charge"

    def test_already_satisfied_goal_returns_empty_plan(self):
        domain = HTNDomain()
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="done",
                    constraints={"battery": 0.5},
                    category="nonexistent")
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.5)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None  # already satisfied = empty plan
        assert result.selected.actions == []

    def test_compound_task_decomposition(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="move_to", cost=2.0,
                                        preconditions={"at_base": True},
                                        effects={"at_target": True}))
        domain.add_operator(HTNOperator(name="scan", cost=1.0,
                                        preconditions={"at_target": True},
                                        effects={"scanned": True}))
        domain.add_method(HTNMethod(
            task="explore",
            subtasks=["move_to", "scan"],
            condition=lambda s: s.get("at_base", False),
        ))
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="explore",
                    constraints={"scanned": True},
                    category="explore")
        mission = Mission("m1", goals=[goal])
        state = RobotState(flags={"at_base": True})
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert len(result.selected.actions) == 2
        assert result.selected.actions[0].name == "move_to"
        assert result.selected.actions[1].name == "scan"

    def test_method_condition_blocks_decomposition(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="charge", cost=1.0,
                                        effects={"battery": 1.0}))
        domain.add_method(HTNMethod(
            task="recharge",
            subtasks=["charge"],
            condition=lambda s: s.get("battery", 1.0) < 0.3,
        ))
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="recharge",
                    constraints={"battery": 1.0},
                    category="recharge")
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.8)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is None  # condition not met

    def test_decomposition_with_multiple_methods(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="walk", cost=3.0,
                                        effects={"at_target": True}))
        domain.add_operator(HTNOperator(name="run", cost=5.0,
                                        effects={"at_target": True}))
        domain.add_method(HTNMethod(
            task="travel",
            subtasks=["walk"],
            condition=lambda s: s.get("battery", 1.0) < 0.5,
        ))
        domain.add_method(HTNMethod(
            task="travel",
            subtasks=["run"],
            condition=lambda s: s.get("battery", 1.0) >= 0.5,
        ))
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="travel",
                    constraints={"at_target": True},
                    category="travel")
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.8)
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is not None
        assert result.selected.actions[0].name == "run"

    def test_operator_precondition_check(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="charge", cost=1.0,
                                        preconditions={"has_charger": True},
                                        effects={"battery": 1.0}))
        domain.add_method(HTNMethod(
            task="recharge",
            subtasks=["charge"],
        ))
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="recharge",
                    constraints={"battery": 1.0},
                    category="recharge")
        mission = Mission("m1", goals=[goal])
        state = RobotState(battery_level=0.5, flags={"has_charger": False})
        result = planner.plan(state, mission, PlanningContext())
        assert result.selected is None  # precondition fails

    def test_multiple_goals_sorted(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="do_a", cost=1.0,
                                        effects={"a_done": True}))
        domain.add_operator(HTNOperator(name="do_b", cost=1.0,
                                        effects={"b_done": True}))
        domain.add_method(HTNMethod(task="task_a", subtasks=["do_a"]))
        domain.add_method(HTNMethod(task="task_b", subtasks=["do_b"]))
        planner = HTNPlanner(domain)
        g_low = Goal(goal_id="g_low", description="low", priority=0.1,
                      constraints={"a_done": True}, category="task_a")
        g_high = Goal(goal_id="g_high", description="high", priority=0.9,
                       constraints={"b_done": True}, category="task_b")
        mission = Mission("m1", goals=[g_low, g_high])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert len(result.candidates) == 2
        assert result.candidates[0].goal_id == "g_high"

    def test_nested_decomposition(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="start", effects={"started": True}))
        domain.add_operator(HTNOperator(name="process", effects={"processed": True},
                                        preconditions={"started": True}))
        domain.add_operator(HTNOperator(name="finish", effects={"finished": True},
                                        preconditions={"processed": True}))
        domain.add_method(HTNMethod(task="production", subtasks=["setup", "run"]))
        domain.add_method(HTNMethod(task="setup", subtasks=["start"]))
        domain.add_method(HTNMethod(task="run", subtasks=["process", "finish"]))
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="produce",
                    constraints={"finished": True}, category="production")
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is not None
        assert len(result.selected.actions) == 3
        names = [a.name for a in result.selected.actions]
        assert names == ["start", "process", "finish"]

    def test_unknown_task_returns_none(self):
        domain = HTNDomain()
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="unknown",
                    constraints={"done": True}, category="nonexistent")
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.selected is None

    def test_domain_property(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="op1"))
        planner = HTNPlanner(domain)
        assert planner.domain.operators["op1"].name == "op1"

    def test_name(self):
        planner = HTNPlanner(HTNDomain())
        assert planner.name == "htn"

    def test_metrics(self):
        domain = HTNDomain()
        domain.add_operator(HTNOperator(name="charge", effects={"done": True}))
        domain.add_method(HTNMethod(task="charge", subtasks=["charge"]))
        planner = HTNPlanner(domain)
        goal = Goal(goal_id="g1", description="charge",
                    constraints={"done": True}, category="charge")
        mission = Mission("m1", goals=[goal])
        result = planner.plan(RobotState(), mission, PlanningContext())
        assert result.metrics.strategy_name == "htn"
        assert result.metrics.planning_latency_ms >= 0
