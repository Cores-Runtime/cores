from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from time import perf_counter

from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy


@dataclass(frozen=True)
class UtilityWeights:
    goal_priority: float = 0.35
    feasibility: float = 0.25
    urgency: float = 0.20
    efficiency: float = 0.20


class UtilityPlanner(PlannerStrategy):
    def __init__(self, weights: Optional[UtilityWeights] = None) -> None:
        self._weights = weights or UtilityWeights()
        self._action_templates: Dict[str, Action] = {}

    @property
    def weights(self) -> UtilityWeights:
        return self._weights

    def register_action(self, category: str, action: Action) -> None:
        self._action_templates[category] = action

    def _compute_utility(
        self, goal: Goal, state: RobotState, mission: Mission, context: PlanningContext
    ) -> float:
        priority_score = goal.priority

        feasible = True
        for key, val in goal.constraints.items():
            if key == "max_battery" and state.battery_level < float(val):
                feasible = False
            elif key == "require_flag" and not state.flags.get(str(val), False):
                feasible = False
        feasibility_score = 1.0 if feasible else 0.0

        urgency_score = 0.5
        if "deadline_cycles" in goal.constraints:
            remaining = int(goal.constraints["deadline_cycles"]) - context.cycle_count
            urgency_score = max(0.0, min(1.0, 1.0 - (remaining / max(remaining, 1))))

        efficiency_score = 1.0 / (goal.priority + 1.0)

        return (
            self._weights.goal_priority * priority_score
            + self._weights.feasibility * feasibility_score
            + self._weights.urgency * urgency_score
            + self._weights.efficiency * efficiency_score
        )

    def _make_action(self, goal: Goal) -> Action:
        if goal.category in self._action_templates:
            base = self._action_templates[goal.category]
            return Action(
                action_id=f"utility_{goal.goal_id}_{base.action_id}",
                name=base.name,
                cost=base.cost,
                duration_cycles=base.duration_cycles,
                preconditions=dict(base.preconditions),
                effects=dict(base.effects),
                required_capabilities=dict(base.required_capabilities),
            )
        return Action(
            action_id=f"utility_{goal.goal_id}_default",
            name=f"pursue_{goal.category}",
            cost=1.0,
            duration_cycles=1,
            effects={"goal_status": "in_progress"},
        )

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

        scored: List[tuple[float, Goal]] = []
        for goal in mission.goals:
            utility = self._compute_utility(goal, state, mission, context)
            scored.append((utility, goal))

        scored.sort(key=lambda x: x[0], reverse=True)

        candidates: List[PlanCandidate] = []
        for utility, goal in scored:
            action = self._make_action(goal)
            plan = PlanCandidate(
                plan_id=f"utility_{goal.goal_id}",
                goal_id=goal.goal_id,
                actions=[action],
                confidence=min(1.0, max(0.0, utility)),
                estimated_cost=action.cost,
                estimated_duration_cycles=action.duration_cycles,
                utility=utility,
                metadata={"weight_scores": {
                    "goal_priority": goal.priority,
                    "feasibility": 1.0 if utility > 0 else 0.0,
                }},
            )
            candidates.append(plan)

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
        return "utility"
