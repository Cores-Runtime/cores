from __future__ import annotations

from typing import Any, Dict

from cores.core.robot_state import RobotState
from cores.core.planning.interface import PlanningContext


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
