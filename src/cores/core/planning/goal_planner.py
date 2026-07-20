from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from time import perf_counter
from collections import deque

from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy


@dataclass(frozen=True)
class ActionModel:
    action_id: str
    name: str
    cost: float = 1.0
    duration_cycles: int = 1
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)


def _extract_state(state: RobotState, context: PlanningContext) -> Dict[str, Any]:
    s: Dict[str, Any] = {
        "battery": state.battery_level,
        "mission_status": state.mission_status,
        "cycle": context.cycle_count,
    }
    s.update(state.flags)
    for k, v in state.sensor_summaries.items():
        s[f"sensor_{k}"] = v
    s.update(state.metadata)
    return s


def _check_conditions(state: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
    for key, val in conditions.items():
        if key not in state or state[key] != val:
            return False
    return True


def _apply_effects(state: Dict[str, Any], effects: Dict[str, Any]) -> Dict[str, Any]:
    new = dict(state)
    new.update(effects)
    return new


class GoalPlanner(PlannerStrategy):
    def __init__(
        self,
        actions: Optional[List[ActionModel]] = None,
        max_depth: int = 10,
        max_candidates: int = 5,
    ) -> None:
        self._actions = list(actions) if actions else []
        self._max_depth = max_depth
        self._max_candidates = max_candidates

    def add_action(self, action: ActionModel) -> None:
        self._actions.append(action)

    def _search(
        self, initial_state: Dict[str, Any], goal_conditions: Dict[str, Any]
    ) -> Optional[List[ActionModel]]:
        if _check_conditions(initial_state, goal_conditions):
            return []

        queue: deque[Tuple[Dict[str, Any], List[ActionModel]]] = deque()
        queue.append((initial_state, []))
        visited = set()

        while queue:
            current_state, plan = queue.popleft()
            state_key = tuple(sorted(current_state.items()))
            if state_key in visited:
                continue
            visited.add(state_key)

            if len(plan) >= self._max_depth:
                continue

            for action in self._actions:
                if not _check_conditions(current_state, action.preconditions):
                    continue
                next_state = _apply_effects(current_state, action.effects)
                next_plan = plan + [action]
                if _check_conditions(next_state, goal_conditions):
                    return next_plan
                queue.append((next_state, next_plan))

        return None

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
            goal_conditions = dict(goal.constraints)
            plan_actions = self._search(world_state, goal_conditions)
            if plan_actions is not None:
                core_actions = [
                    Action(
                        action_id=a.action_id,
                        name=a.name,
                        cost=a.cost,
                        duration_cycles=a.duration_cycles,
                        preconditions=dict(a.preconditions),
                        effects=dict(a.effects),
                    )
                    for a in plan_actions
                ]
                total_cost = sum(a.cost for a in plan_actions)
                total_duration = sum(a.duration_cycles for a in plan_actions)
                plan_id = f"goal_{goal.goal_id}"
                candidate = PlanCandidate(
                    plan_id=plan_id,
                    goal_id=goal.goal_id,
                    actions=core_actions,
                    confidence=1.0 / (1.0 + total_cost),
                    estimated_cost=total_cost,
                    estimated_duration_cycles=total_duration,
                    utility=goal.priority / (1.0 + total_cost),
                    metadata={"plan_length": len(plan_actions)},
                )
                candidates.append(candidate)

        candidates.sort(key=lambda c: c.utility, reverse=True)
        candidates = candidates[: self._max_candidates]
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
        return "goal"
