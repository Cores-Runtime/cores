from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from time import perf_counter

from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal, Action, PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy


class BTNode(ABC):
    @abstractmethod
    def evaluate(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> Tuple[bool, List[Action]]:
        ...

    def name(self) -> str:
        return self.__class__.__name__


@dataclass
class BTCondition(BTNode):
    predicate: Callable[[RobotState, Mission, PlanningContext], bool]
    label: str = ""

    def evaluate(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> Tuple[bool, List[Action]]:
        try:
            return self.predicate(state, mission, context), []
        except Exception:
            return False, []

    def name(self) -> str:
        return self.label or "Condition"


@dataclass
class BTAction(BTNode):
    action: Action
    condition: Optional[Callable[[RobotState, Mission, PlanningContext], bool]] = None
    label: str = ""

    def evaluate(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> Tuple[bool, List[Action]]:
        if self.condition is not None:
            try:
                if not self.condition(state, mission, context):
                    return False, []
            except Exception:
                return False, []
        return True, [self.action]

    def name(self) -> str:
        return self.label or self.action.name


@dataclass
class BTSequence(BTNode):
    children: List[BTNode] = field(default_factory=list)
    label: str = ""

    def evaluate(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> Tuple[bool, List[Action]]:
        actions: List[Action] = []
        for child in self.children:
            success, child_actions = child.evaluate(state, mission, context)
            actions.extend(child_actions)
            if not success:
                return False, actions
        return True, actions

    def name(self) -> str:
        return self.label or "Sequence"


@dataclass
class BTSelector(BTNode):
    children: List[BTNode] = field(default_factory=list)
    label: str = ""

    def evaluate(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> Tuple[bool, List[Action]]:
        for child in self.children:
            success, child_actions = child.evaluate(state, mission, context)
            if success:
                return True, child_actions
        return False, []

    def name(self) -> str:
        return self.label or "Selector"


@dataclass
class BTInverter(BTNode):
    child: BTNode
    label: str = ""

    def evaluate(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> Tuple[bool, List[Action]]:
        success, actions = self.child.evaluate(state, mission, context)
        return (not success, actions)

    def name(self) -> str:
        return self.label or "Inverter"


class BehaviorTreePlanner(PlannerStrategy):
    def __init__(self, root: BTNode, goal: Goal) -> None:
        self._root = root
        self._goal = goal

    def plan(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> PlanningResult:
        start = perf_counter()
        goal_id = self._goal.goal_id

        if mission.goals and not any(g.goal_id == goal_id for g in mission.goals):
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

        try:
            success, actions = self._root.evaluate(state, mission, context)
        except Exception:
            success, actions = False, []

        if not success or not actions:
            elapsed = (perf_counter() - start) * 1000
            return PlanningResult(
                candidates=[],
                selected=None,
                metrics=PlanningMetrics(
                    planning_latency_ms=elapsed,
                    candidates_generated=0,
                    goals_considered=1,
                    strategy_name=self.name,
                ),
            )

        total_cost = sum(a.cost for a in actions)
        total_duration = sum(a.duration_cycles for a in actions)
        plan = PlanCandidate(
            plan_id=f"bt_{goal_id}",
            goal_id=goal_id,
            actions=actions,
            confidence=1.0,
            estimated_cost=total_cost,
            estimated_duration_cycles=total_duration,
            utility=1.0,
            metadata={"tree_path": self._root.name()},
        )
        elapsed = (perf_counter() - start) * 1000
        return PlanningResult(
            candidates=[plan],
            selected=plan,
            metrics=PlanningMetrics(
                planning_latency_ms=elapsed,
                candidates_generated=1,
                goals_considered=1,
                strategy_name=self.name,
            ),
        )

    @property
    def name(self) -> str:
        return "behavior_tree"
