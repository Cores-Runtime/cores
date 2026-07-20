from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from time import perf_counter

from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy


@dataclass(frozen=True)
class ReactiveRule:
    condition: Callable[[RobotState, Mission, PlanningContext], bool]
    goal: Goal
    action: Action
    priority: int = 0
    description: str = ""


class ReactivePlanner(PlannerStrategy):
    def __init__(self, rules: Optional[List[ReactiveRule]] = None) -> None:
        self._rules = list(rules) if rules else []

    @property
    def rules(self) -> List[ReactiveRule]:
        return list(self._rules)

    def add_rule(self, rule: ReactiveRule) -> None:
        self._rules.append(rule)

    def add_rules(self, rules: List[ReactiveRule]) -> None:
        self._rules.extend(rules)

    def clear_rules(self) -> None:
        self._rules.clear()

    def plan(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> PlanningResult:
        start = perf_counter()
        matching: List[ReactiveRule] = []
        goals_considered = 0

        for rule in self._rules:
            try:
                if rule.condition(state, mission, context):
                    matching.append(rule)
            except Exception:
                continue
            goals_considered += 1

        if not matching:
            elapsed = (perf_counter() - start) * 1000
            return PlanningResult(
                candidates=[],
                selected=None,
                metrics=PlanningMetrics(
                    planning_latency_ms=elapsed,
                    candidates_generated=0,
                    goals_considered=goals_considered,
                    strategy_name=self.name,
                ),
            )

        matching.sort(key=lambda r: r.priority, reverse=True)
        best = matching[0]
        plan = PlanCandidate(
            plan_id=f"reactive_{best.goal.goal_id}_{best.action.action_id}",
            goal_id=best.goal.goal_id,
            actions=[best.action],
            confidence=1.0,
            estimated_cost=best.action.cost,
            estimated_duration_cycles=best.action.duration_cycles,
            metadata={"rule": best.description, "priority": best.priority},
        )
        elapsed = (perf_counter() - start) * 1000
        return PlanningResult(
            candidates=[plan],
            selected=plan,
            metrics=PlanningMetrics(
                planning_latency_ms=elapsed,
                candidates_generated=1,
                goals_considered=goals_considered,
                strategy_name=self.name,
            ),
        )

    @property
    def name(self) -> str:
        return "reactive"
