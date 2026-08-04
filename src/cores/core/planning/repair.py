from __future__ import annotations

from typing import Any, Dict, List, Optional

from cores.core.robot_state import RobotState
from cores.core.planning.types import PlanCandidate
from cores.core.planning.interface import PlanningContext
from cores.core.planning.state import _extract_state, _check_conditions, _apply_effects


def plan_still_valid(
    state: RobotState, context: PlanningContext, plan: PlanCandidate
) -> bool:
    """Re-check the plan's preconditions progressively against current state."""
    current = _extract_state(state, context)
    for action in plan.actions:
        if not _check_conditions(current, action.preconditions):
            return False
        current = _apply_effects(current, action.effects)
    return True


def first_blocked_index(
    state: RobotState, context: PlanningContext, plan: PlanCandidate
) -> Optional[int]:
    """Return the index of the first action whose preconditions fail.

    The check is progressive: each action's preconditions are tested against
    the state produced by applying the effects of the actions before it.
    """
    current = _extract_state(state, context)
    for i, action in enumerate(plan.actions):
        if not _check_conditions(current, action.preconditions):
            return i
        current = _apply_effects(current, action.effects)
    return None


def state_after_actions(
    state: RobotState,
    context: PlanningContext,
    actions: List[Any],
) -> Dict[str, Any]:
    """Project the state after applying the effects of the given actions."""
    current = _extract_state(state, context)
    for action in actions:
        current = _apply_effects(current, action.effects)
    return current
