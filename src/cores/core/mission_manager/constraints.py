from __future__ import annotations

from typing import Any

from cores.core.robot_state import RobotState
from cores.core.planning.types import Goal


class GoalConstraintEvaluator:
    """Optional automatic goal completion check.

    Standalone on purpose: it does not depend on the explicit completion API,
    and the explicit API does not depend on it. It reads Goal.constraints and
    checks each entry against the current RobotState (flags, metadata, or a
    RobotState field). A goal with no constraints is never auto-completed; the
    explicit API is the default path.
    """

    def is_satisfied(self, goal: Goal, state: RobotState) -> bool:
        constraints = goal.constraints or {}
        if not constraints:
            return False
        for key, expected in constraints.items():
            if key == "depends_on":
                continue
            actual = self._resolve(state, key)
            if actual is None or actual != expected:
                return False
        return True

    @staticmethod
    def _resolve(state: RobotState, key: str) -> Any:
        if key in state.flags:
            return state.flags[key]
        if key in state.metadata:
            return state.metadata[key]
        if hasattr(state, key):
            return getattr(state, key)
        return None


class NoAutoCompletion(GoalConstraintEvaluator):
    """A disabled evaluator: automatic completion is turned off.

    Present so MissionManager can express 'no automatic completion' explicitly
    instead of relying on a None check that couples the two mechanisms.
    """

    def is_satisfied(self, goal: Goal, state: RobotState) -> bool:
        return False
