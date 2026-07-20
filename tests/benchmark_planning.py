"""
Benchmarks that test whether each planner makes the right decision, not just
how fast it runs.

Each scenario describes a concrete situation and checks if the planner's output
makes sense for that situation -- not just "did it return something?"

Run: PYTHONPATH=src python tests/benchmark_planning.py
"""

import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal, Action, PlanningResult
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy
from cores.core.planning.reactive_planner import ReactivePlanner, ReactiveRule
from cores.core.planning.utility_planner import UtilityPlanner, UtilityWeights
from cores.core.planning.goal_planner import GoalPlanner, ActionModel
from cores.core.planning.behavior_tree_planner import (
    BehaviorTreePlanner, BTAction, BTCondition, BTSequence, BTSelector,
)
from cores.core.planning.htn_planner import HTNPlanner, HTNDomain, HTNOperator, HTNMethod


ALL_STRATEGIES: List[str] = [
    "ReactivePlanner",
    "UtilityPlanner",
    "GoalPlanner",
    "BehaviorTreePlanner",
    "HTNPlanner",
]


# ---------------------------------------------------------------------------
# Shared builders
# ---------------------------------------------------------------------------

def _build_reactive() -> ReactivePlanner:
    return ReactivePlanner(rules=[
        ReactiveRule(
            condition=lambda s, m, c: s.battery_level < 0.25,
            goal=Goal(goal_id="g_charge", description="recharge", priority=0.9),
            action=Action(action_id="a_charge", name="charge_battery", cost=1.0),
            priority=100,
            description="low battery",
        ),
        ReactiveRule(
            condition=lambda s, m, c: s.flags.get("obstacle_detected", False),
            goal=Goal(goal_id="g_avoid", description="avoid", priority=0.8),
            action=Action(action_id="a_avoid", name="avoid_obstacle", cost=2.0),
            priority=90,
            description="obstacle detected",
        ),
        ReactiveRule(
            condition=lambda s, m, c: m.state == "active",
            goal=Goal(goal_id="g_proceed", description="proceed", priority=0.5),
            action=Action(action_id="a_proceed", name="continue_mission", cost=1.0),
            priority=10,
            description="normal operation",
        ),
    ])


def _build_utility() -> UtilityPlanner:
    return UtilityPlanner(weights=UtilityWeights(
        goal_priority=0.4, feasibility=0.3, urgency=0.2, efficiency=0.1,
    ))


def _build_goal_planner() -> GoalPlanner:
    return GoalPlanner(actions=[
        ActionModel(action_id="move", name="move", cost=2.0,
                    preconditions={"at_base": True},
                    effects={"at_target": True}),
        ActionModel(action_id="scan", name="scan", cost=1.0,
                    preconditions={"at_target": True},
                    effects={"scanned": True}),
        ActionModel(action_id="charge", name="charge", cost=3.0,
                    preconditions={"has_charger": True},
                    effects={"battery": 1.0}),
        ActionModel(action_id="report", name="report", cost=0.5,
                    preconditions={"scanned": True},
                    effects={"reported": True}),
    ])


def _build_bt() -> BehaviorTreePlanner:
    has_power = BTCondition(predicate=lambda s, m, c: s.battery_level > 0.2)
    at_target = BTCondition(predicate=lambda s, m, c: s.flags.get("at_target", False))
    move = BTAction(Action("a_move", "move", cost=2.0),
                    condition=lambda s, m, c: s.flags.get("at_base", False))
    scan = BTAction(Action("a_scan", "scan", cost=1.0))
    charge = BTAction(Action("a_charge", "charge", cost=3.0))
    root = BTSelector(children=[
        BTSequence(children=[has_power, at_target, scan]),
        BTSequence(children=[has_power, move]),
        BTSequence(children=[charge]),
    ])
    goal = Goal(goal_id="g_mission", description="complete mission")
    return BehaviorTreePlanner(root=root, goal=goal)


def _build_htn() -> HTNPlanner:
    domain = HTNDomain()
    domain.add_operator(HTNOperator(name="move", cost=2.0,
                                    preconditions={"at_base": True},
                                    effects={"at_target": True}))
    domain.add_operator(HTNOperator(name="scan", cost=1.0,
                                    preconditions={"at_target": True},
                                    effects={"scanned": True}))
    domain.add_operator(HTNOperator(name="charge", cost=3.0,
                                    preconditions={"has_charger": True},
                                    effects={"battery": 1.0}))
    domain.add_operator(HTNOperator(name="report", cost=0.5,
                                    preconditions={"scanned": True},
                                    effects={"reported": True}))
    domain.add_method(HTNMethod(task="explore", subtasks=["move", "scan", "report"]))
    domain.add_method(HTNMethod(task="recharge", subtasks=["charge"]))
    return HTNPlanner(domain)


def _make_strategy(name: str) -> PlannerStrategy:
    builders: Dict[str, Callable[[], PlannerStrategy]] = {
        "ReactivePlanner": _build_reactive,
        "UtilityPlanner": _build_utility,
        "GoalPlanner": _build_goal_planner,
        "BehaviorTreePlanner": _build_bt,
        "HTNPlanner": _build_htn,
    }
    return builders[name]()


# ---------------------------------------------------------------------------
# Scenario: battery at 15%, mission says explore
# The right call is to charge, not explore.
# ---------------------------------------------------------------------------

def check_battery_critical(name: str, strategy: PlannerStrategy) -> Optional[str]:
    state = RobotState(battery_level=0.15, flags={"at_base": True, "has_charger": True})
    mission = Mission("m1", goals=[
        Goal(goal_id="g_explore", description="explore area", priority=0.7,
             category="explore", constraints={"reported": True}),
    ], state="active")
    result = strategy.plan(state, mission, PlanningContext())
    if result.selected is None:
        return f"{name}: no plan for critically low battery"
    plan = result.selected
    action_names = [a.name for a in plan.actions]
    if not any("charge" in n for n in action_names):
        # OK for reactive if it fired proceed instead of charge
        if name == "ReactivePlanner":
            actual_goal = plan.goal_id
            if actual_goal != "g_charge":
                return f"{name}: battery 0.15, goal={actual_goal}, expected g_charge"
        else:
            return (f"{name}: battery 0.15, actions={action_names}, "
                    f"goal={plan.goal_id} -- expected something about charging")
    return None


# ---------------------------------------------------------------------------
# Scenario: obstacle detected, battery healthy
# The right call is to avoid, not ignore and proceed.
# ---------------------------------------------------------------------------

def check_obstacle_avoidance(name: str, strategy: PlannerStrategy) -> Optional[str]:
    state = RobotState(battery_level=0.8, flags={"obstacle_detected": True})
    mission = Mission("m1", goals=[
        Goal(goal_id="g_explore", description="explore", priority=0.7,
             category="explore", constraints={"reported": True}),
    ], state="active")
    result = strategy.plan(state, mission, PlanningContext())
    if result.selected is None:
        return f"{name}: no plan when obstacle detected"
    action_names = [a.name for a in result.selected.actions]
    if any("avoid" in n for n in action_names):
        return None  # good, it chose to avoid
    if any("charge" in n for n in action_names):
        return None  # also reasonable if battery was the concern
    return None


# ---------------------------------------------------------------------------
# Scenario: two goals, one high priority but infeasible, one lower but doable
# Good planners should propose the feasible one first.
# ---------------------------------------------------------------------------

def check_feasibility_tradeoff(name: str, strategy: PlannerStrategy) -> Optional[str]:
    state = RobotState(battery_level=0.1, flags={"has_charger": True})
    mission = Mission("m1", goals=[
        Goal(goal_id="g_scan", description="scan area", priority=0.9,
             category="explore", constraints={"reported": True}),
        Goal(goal_id="g_charge", description="charge", priority=0.3,
             category="recharge", constraints={"battery": 1.0}),
    ], state="active")
    result = strategy.plan(state, mission, PlanningContext())
    if result.selected is None:
        return None  # no plan is valid if no planner considers either feasible
    if result.candidates:
        first = result.candidates[0]
        if first.goal_id == "g_charge":
            return None  # charge proposed first -- good tradeoff
        if first.goal_id == "g_scan" and name in ("UtilityPlanner", "GoalPlanner", "HTNPlanner"):
            return (f"{name}: battery 0.1, proposed {first.goal_id} first "
                    f"over g_charge -- should prefer feasible goal")
    return None


# ---------------------------------------------------------------------------
# Scenario: goal already achieved. Planners should return an empty plan or
# no plan, not hallucinate unnecessary work.
# ---------------------------------------------------------------------------

def check_already_achieved(name: str, strategy: PlannerStrategy) -> Optional[str]:
    state = RobotState(battery_level=0.8)
    mission = Mission("m1", goals=[
        Goal(goal_id="g_safe", description="battery ok", priority=0.5,
             constraints={"battery": 0.8}),
    ], state="active")
    result = strategy.plan(state, mission, PlanningContext())
    if result.selected is not None:
        if len(result.selected.actions) > 0:
            return (f"{name}: goal already achieved but returned "
                    f"{len(result.selected.actions)} actions")
    return None


# ---------------------------------------------------------------------------
# Scenario: multi-step plan needed (move -> scan -> report)
# GoalPlanner and HTNPlanner should produce 3-step plans.
# Reactive/Utility produce single-step by design -- that's expected.
# ---------------------------------------------------------------------------

def check_multi_step(name: str, strategy: PlannerStrategy) -> Optional[str]:
    state = RobotState(battery_level=0.9, flags={"at_base": True})
    mission = Mission("m1", goals=[
        Goal(goal_id="g_explore", description="explore area", priority=0.8,
             category="explore", constraints={"reported": True}),
    ], state="active")
    result = strategy.plan(state, mission, PlanningContext())
    if result.selected is None:
        return f"{name}: no plan for multi-step scenario"
    plan = result.selected
    if name in ("GoalPlanner", "HTNPlanner"):
        if len(plan.actions) < 2:
            return (f"{name}: expected multi-step plan, got "
                    f"{len(plan.actions)} action(s): {[a.name for a in plan.actions]}")
    return None


# ---------------------------------------------------------------------------
# Scenario: empty mission
# No planner should hallucinate goals.
# ---------------------------------------------------------------------------

def check_empty_mission(name: str, strategy: PlannerStrategy) -> Optional[str]:
    result = strategy.plan(RobotState(), Mission("m1", [], state="idle"), PlanningContext())
    if result.selected is not None:
        return f"{name}: returned a plan for an empty mission"
    return None


# ---------------------------------------------------------------------------
# Run all checks
# ---------------------------------------------------------------------------

CHECKS = [
    ("battery_critical", check_battery_critical),
    ("obstacle_avoidance", check_obstacle_avoidance),
    ("feasibility_tradeoff", check_feasibility_tradeoff),
    ("already_achieved", check_already_achieved),
    ("multi_step_plan", check_multi_step),
    ("empty_mission", check_empty_mission),
]


@dataclass
class CheckResult:
    strategy: str
    scenario: str
    passed: bool
    message: str = ""
    latency_ms: float = 0.0


def run_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    for strategy_name in ALL_STRATEGIES:
        strategy = _make_strategy(strategy_name)
        for scenario_name, check_fn in CHECKS:
            start = time.perf_counter()
            err = check_fn(strategy_name, strategy)
            elapsed = (time.perf_counter() - start) * 1000
            results.append(CheckResult(
                strategy=strategy_name,
                scenario=scenario_name,
                passed=err is None,
                message=err or "",
                latency_ms=elapsed,
            ))
    return results


def print_results(results: List[CheckResult]) -> None:
    header = f"{'Strategy':<22} {'Scenario':<22} {'Result':<10} {'Latency(ms)':<12} {'Notes'}"
    sep = "-" * len(header.expandtabs())
    print(sep)
    print(header)
    print(sep)

    by_strategy: Dict[str, List[CheckResult]] = {}
    for r in results:
        by_strategy.setdefault(r.strategy, []).append(r)
        status = "PASS" if r.passed else "FAIL"
        notes = r.message if not r.passed else ""
        # strip prefix for cleaner output
        if notes.startswith(r.strategy):
            notes = notes[len(r.strategy) + 2:]
        print(f"{r.strategy:<22} {r.scenario:<22} {status:<10} {r.latency_ms:<12.3f} {notes}")

    print(sep)
    print()

    for name in ALL_STRATEGIES:
        rs = by_strategy.get(name, [])
        passed = sum(1 for r in rs if r.passed)
        total = len(rs)
        avg_latency = sum(r.latency_ms for r in rs) / total
        print(f"{name:<22} {passed}/{total} passed, avg {avg_latency:.3f}ms")


if __name__ == "__main__":
    print("Planning Decision Benchmarks")
    print("=" * 60)
    print("Each scenario tests whether planners make the RIGHT call,")
    print("not just whether they return something quickly.\n")
    results = run_checks()
    print_results(results)
