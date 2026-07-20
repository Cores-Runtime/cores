from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from time import perf_counter

from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy
from cores.core.planning.goal_planner import _extract_state, _check_conditions


@dataclass(frozen=True)
class HTNOperator:
    name: str
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    cost: float = 1.0
    duration_cycles: int = 1


@dataclass(frozen=True)
class HTNMethod:
    task: str
    subtasks: List[str]
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None


class HTNDomain:
    def __init__(self) -> None:
        self.operators: Dict[str, HTNOperator] = {}
        self.methods: Dict[str, List[HTNMethod]] = {}

    def add_operator(self, op: HTNOperator) -> None:
        self.operators[op.name] = op

    def add_method(self, method: HTNMethod) -> None:
        if method.task not in self.methods:
            self.methods[method.task] = []
        self.methods[method.task].append(method)


def _is_primitive(task: str, domain: HTNDomain) -> bool:
    return task in domain.operators


def _apply_effects(state: Dict[str, Any], effects: Dict[str, Any]) -> Dict[str, Any]:
    new = dict(state)
    new.update(effects)
    return new


def _decompose(
    task: str,
    domain: HTNDomain,
    state: Dict[str, Any],
    depth: int = 0,
    max_depth: int = 20,
) -> Optional[Tuple[List[HTNOperator], float]]:
    if depth > max_depth:
        return None
    if _is_primitive(task, domain):
        op = domain.operators[task]
        if _check_conditions(state, op.preconditions):
            return ([op], op.cost)
        return None
    if task not in domain.methods:
        return None
    for method in domain.methods[task]:
        if method.condition is not None and not method.condition(state):
            continue
        all_ops: List[HTNOperator] = []
        total_cost = 0.0
        current_state = dict(state)
        valid = True
        for subtask in method.subtasks:
            result = _decompose(subtask, domain, current_state, depth + 1, max_depth)
            if result is None:
                valid = False
                break
            sub_ops, sub_cost = result
            for op in sub_ops:
                current_state.update(op.effects)
            all_ops.extend(sub_ops)
            total_cost += sub_cost
        if valid:
            return (all_ops, total_cost)
    return None


class HTNPlanner(PlannerStrategy):
    def __init__(self, domain: HTNDomain, max_depth: int = 20) -> None:
        self._domain = domain
        self._max_depth = max_depth

    @property
    def domain(self) -> HTNDomain:
        return self._domain

    def _plan_for_goal(
        self, state: Dict[str, Any], goal: Goal
    ) -> Optional[Tuple[List[HTNOperator], float]]:
        goal_conditions = dict(goal.constraints)
        if _check_conditions(state, goal_conditions):
            return ([], 0.0)
        task_name = goal.category
        if task_name not in self._domain.methods and task_name not in self._domain.operators:
            return None
        return _decompose(task_name, self._domain, state, max_depth=self._max_depth)

    def plan(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> PlanningResult:
        start = perf_counter()
        if not mission.goals:
            elapsed = (perf_counter() - start) * 1000
            return PlanningResult(
                candidates=[],
                selected=None,
                metrics=PlanningMetrics(
                    planning_latency_ms=elapsed,
                    candidates_generated=0,
                    goals_considered=0,
                    strategy_name=self.name,
                ),
            )

        world_state = _extract_state(state, context)
        candidates: List[PlanCandidate] = []

        for goal in mission.goals:
            result = self._plan_for_goal(world_state, goal)
            if result is not None:
                ops, total_cost = result
                actions = [
                    Action(
                        action_id=op.name,
                        name=op.name,
                        cost=op.cost,
                        duration_cycles=op.duration_cycles,
                        preconditions=dict(op.preconditions),
                        effects=dict(op.effects),
                    )
                    for op in ops
                ]
                plan = PlanCandidate(
                    plan_id=f"htn_{goal.goal_id}",
                    goal_id=goal.goal_id,
                    actions=actions,
                    confidence=1.0 / (1.0 + total_cost) if total_cost > 0 else 1.0,
                    estimated_cost=total_cost,
                    estimated_duration_cycles=sum(op.duration_cycles for op in ops),
                    utility=goal.priority / (1.0 + total_cost),
                    metadata={"decomposition_depth": len(ops)},
                )
                candidates.append(plan)

        candidates.sort(key=lambda c: c.utility, reverse=True)
        selected = candidates[0] if candidates else None

        elapsed = (perf_counter() - start) * 1000
        return PlanningResult(
            candidates=candidates,
            selected=selected,
            metrics=PlanningMetrics(
                planning_latency_ms=elapsed,
                candidates_generated=len(candidates),
                goals_considered=len(mission.goals),
                strategy_name=self.name,
            ),
        )

    @property
    def name(self) -> str:
        return "htn"
