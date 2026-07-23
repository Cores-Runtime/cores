from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

from cores.core.robot_state import RobotState
from cores.core.planning.types import PlanningResult, PlanCandidate
from cores.core.planning.mission import Mission

if TYPE_CHECKING:
    from cores.core.memory import Memory


@dataclass
class PlanningContext:
    cycle_count: int = 0
    compute_budget: float = 1.0
    time_budget_ms: float = 100.0
    world_state: Dict[str, Any] = field(default_factory=dict)
    environment_changed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory: Optional[Memory] = None


class PlannerStrategy(ABC):
    @abstractmethod
    def plan(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> PlanningResult:
        ...

    def replan(
        self,
        state: RobotState,
        mission: Mission,
        context: PlanningContext,
        previous_plan: PlanCandidate,
        changes: Dict[str, Any],
    ) -> Optional[PlanningResult]:
        return None

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class Planner:
    def __init__(self, strategy: PlannerStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> PlannerStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, s: PlannerStrategy) -> None:
        self._strategy = s

    def plan(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> PlanningResult:
        return self._strategy.plan(state, mission, context)

    def replan(
        self,
        state: RobotState,
        mission: Mission,
        context: PlanningContext,
        previous_plan: PlanCandidate,
        changes: Dict[str, Any],
    ) -> Optional[PlanningResult]:
        return self._strategy.replan(state, mission, context, previous_plan, changes)
