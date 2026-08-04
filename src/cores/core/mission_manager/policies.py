from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set

from cores.core.mission_manager.types import (
    FailureAction,
    MissionRecord,
    MissionStatus,
)


class MissionSelectionPolicy(ABC):
    """Decides which mission should be ACTIVE right now."""

    @abstractmethod
    def select(self, records: List[MissionRecord]) -> Optional[MissionRecord]:
        """Return the mission to activate, or None if nothing can run."""


class PriorityMissionSelectionPolicy(MissionSelectionPolicy):
    """Selects the highest-priority eligible mission.

    Preemption happens in the manager: activating a mission other than the
    current one returns the current mission to READY, so it becomes eligible
    again the moment the higher-priority work finishes. No priorities are
    hardcoded here; each mission carries its own priority.
    """

    def select(self, records: List[MissionRecord]) -> Optional[MissionRecord]:
        eligible = [
            record
            for record in records
            if record.status in (MissionStatus.READY, MissionStatus.ACTIVE)
        ]
        if not eligible:
            return None
        return max(eligible, key=lambda record: record.mission.priority)


class MissionRetryPolicy(ABC):
    """Decides whether a failed goal may be attempted again."""

    @abstractmethod
    def should_retry(self, mission_id: str, goal_id: str, attempts: int) -> bool:
        ...


class DefaultMissionRetryPolicy(MissionRetryPolicy):
    """Retries up to max_attempts, then gives up."""

    def __init__(self, max_attempts: int = 2) -> None:
        self.max_attempts = max_attempts

    def should_retry(self, mission_id: str, goal_id: str, attempts: int) -> bool:
        return attempts < self.max_attempts


class MissionFailurePolicy(ABC):
    """Decides what happens to a mission when a goal fails."""

    @abstractmethod
    def decide(self, mission_id: str, goal_id: str, attempts: int) -> FailureAction:
        ...


class DefaultMissionFailurePolicy(MissionFailurePolicy):
    """Retries until the retry policy says stop, then fails the mission."""

    def __init__(self, retry_policy: Optional[MissionRetryPolicy] = None) -> None:
        self.retry_policy = retry_policy or DefaultMissionRetryPolicy()

    def decide(self, mission_id: str, goal_id: str, attempts: int) -> FailureAction:
        if self.retry_policy.should_retry(mission_id, goal_id, attempts):
            return FailureAction.RETRY
        return FailureAction.FAIL_MISSION


class MissionTransitionPolicy(ABC):
    """Owns the legal lifecycle transitions."""

    @abstractmethod
    def can_transition(self, source: MissionStatus, target: MissionStatus) -> bool:
        ...


class DefaultMissionTransitionPolicy(MissionTransitionPolicy):
    """Default lifecycle rules:

    - NEW missions are not executable.
    - READY missions may start.
    - ACTIVE missions own the planner.
    - PAUSED missions retain progress.
    - COMPLETED missions never resume.
    - FAILED missions may optionally retry.
    - CANCELLED missions never resume.
    """

    _ALLOWED: Dict[MissionStatus, Set[MissionStatus]] = {
        MissionStatus.NEW: {MissionStatus.READY, MissionStatus.CANCELLED},
        MissionStatus.READY: {MissionStatus.ACTIVE, MissionStatus.CANCELLED},
        MissionStatus.ACTIVE: {
            MissionStatus.READY,
            MissionStatus.PAUSED,
            MissionStatus.COMPLETED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        },
        MissionStatus.PAUSED: {
            MissionStatus.READY,
            MissionStatus.ACTIVE,
            MissionStatus.CANCELLED,
        },
        MissionStatus.FAILED: {MissionStatus.READY, MissionStatus.CANCELLED},
        MissionStatus.COMPLETED: set(),
        MissionStatus.CANCELLED: set(),
    }

    def can_transition(self, source: MissionStatus, target: MissionStatus) -> bool:
        return target in self._ALLOWED.get(source, set())
