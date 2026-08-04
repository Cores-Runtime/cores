from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Dict, Optional

from cores.core.planning.mission import Mission
from cores.core.planning.types import Goal


class MissionStatus(StrEnum):
    """Lifecycle states of a mission.

    Values are lowercase so they can be written directly into
    RobotState.mission_status for the scheduler and the runtime bridge.
    """

    NEW = "new"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalStatus(StrEnum):
    """Lifecycle states of a goal inside a mission."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class FailureAction(StrEnum):
    """What the failure policy decided should happen after a goal fails."""

    RETRY = "retry"
    PAUSE = "pause"
    FAIL_MISSION = "fail_mission"
    CANCEL_MISSION = "cancel_mission"


@dataclass
class MissionRecord:
    """Authoritative runtime state of one submitted mission.

    The Mission dataclass is intentionally left untouched for backward
    compatibility. This record owns the lifecycle: status, per-goal statuses,
    the active goal, and progress.
    """

    mission: Mission
    status: MissionStatus = MissionStatus.NEW
    goal_statuses: Dict[str, GoalStatus] = field(default_factory=dict)
    active_goal_index: Optional[int] = None
    progress: float = 0.0
    attempt_counts: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.goal_statuses:
            self.goal_statuses = {
                goal.goal_id: GoalStatus.PENDING for goal in self.mission.goals
            }

    @property
    def mission_id(self) -> str:
        return self.mission.mission_id

    def goal(self, index: int) -> Optional[Goal]:
        goals = self.mission.goals
        if 0 <= index < len(goals):
            return goals[index]
        return None

    def completed_count(self) -> int:
        return sum(
            1 for status in self.goal_statuses.values() if status is GoalStatus.COMPLETED
        )

    def recompute_progress(self) -> float:
        total = len(self.mission.goals)
        self.progress = self.completed_count() / total if total else 0.0
        return self.progress


@dataclass
class MissionContext:
    """What Mission Manager hands to Planning for the current cycle.

    Planning receives one active goal only. It never sees other missions or
    inactive goals.
    """

    current_mission: Optional[Mission] = None
    current_goal: Optional[Goal] = None
    mission_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.current_mission is not None and self.current_goal is not None
