from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.safety_supervisor.types import (
    SafetyDecision,
    SafetyReason,
    SafetyPolicyResult,
)


class SafetyPolicy(ABC):
    """Abstract base class for safety policies.

    A safety policy evaluates the current robot state and returns a safety decision.
    Policies must not depend on other policies' outputs.
    """

    @abstractmethod
    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyPolicyResult:
        """Evaluate the current state and return a safety decision."""
        ...


# ---------------------------------------------------------------------------
# Battery Safety Policy
# ---------------------------------------------------------------------------

class BatterySafetyPolicy:
    """Evaluates battery level and returns safety decisions.

    If battery level is unavailable, returns ALLOW.
    """

    def __init__(
        self,
        critical_threshold: float = 0.10,
        warning_threshold: float = 0.25,
    ) -> None:
        self.critical = critical_threshold
        self.warning = warning_threshold

    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyPolicyResult:
        if state.battery_level is None:
            return SafetyPolicyResult(
                decision=SafetyDecision.ALLOW,
                reason=SafetyReason.BATTERY_LOW,
                policy_name="BatterySafetyPolicy",
            )

        if state.battery_level <= self.critical:
            return SafetyPolicyResult(
                decision=SafetyDecision.EMERGENCY_STOP,
                reason=SafetyReason.BATTERY_CRITICAL,
                policy_name="BatterySafetyPolicy",
            )

        if state.battery_level <= self.warning:
            return SafetyPolicyResult(
                decision=SafetyDecision.PAUSE,
                reason=SafetyReason.BATTERY_LOW,
                policy_name="BatterySafetyPolicy",
            )

        return SafetyPolicyResult(
            decision=SafetyDecision.ALLOW,
            reason=SafetyReason.BATTERY_LOW,
            policy_name="BatterySafetyPolicy",
        )


# ---------------------------------------------------------------------------
# Collision Safety Policy
# ---------------------------------------------------------------------------

class CollisionSafetyPolicy:
    """Evaluates collision distance from sensor summaries.

    If collision distance is not available in sensor_summaries, returns ALLOW.
    This makes the policy an optional capability that activates only when
    collision information is provided by the perception system.
    """

    def __init__(
        self,
        critical_distance: float = 0.3,
        warning_distance: float = 0.8,
    ) -> None:
        self.critical = critical_distance
        self.warning = warning_distance

    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyPolicyResult:
        collision_dist = state.sensor_summaries.get("collision_distance")
        if collision_dist is None:
            return SafetyPolicyResult(
                decision=SafetyDecision.ALLOW,
                reason=SafetyReason.COLLISION_RISK,
                policy_name="CollisionSafetyPolicy",
            )

        if collision_dist <= self.critical:
            return SafetyPolicyResult(
                decision=SafetyDecision.EMERGENCY_STOP,
                reason=SafetyReason.COLLISION_RISK,
                policy_name="CollisionSafetyPolicy",
            )

        if collision_dist <= self.warning:
            return SafetyPolicyResult(
                decision=SafetyDecision.PAUSE,
                reason=SafetyReason.COLLISION_RISK,
                policy_name="CollisionSafetyPolicy",
            )

        return SafetyPolicyResult(
            decision=SafetyDecision.ALLOW,
            reason=SafetyReason.COLLISION_RISK,
            policy_name="CollisionSafetyPolicy",
        )


# ---------------------------------------------------------------------------
# Human Safety Policy
# ---------------------------------------------------------------------------

class HumanSafetyPolicy:
    """Evaluates human presence from robot flags.

    If human_detected flag is not present, returns ALLOW.
    Detection is the responsibility of the perception system, not Safety.
    """

    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyPolicyResult:
        human_detected = state.flags.get("human_detected")
        if not human_detected:
            return SafetyPolicyResult(
                decision=SafetyDecision.ALLOW,
                reason=SafetyReason.HUMAN_DETECTED,
                policy_name="HumanSafetyPolicy",
            )

        return SafetyPolicyResult(
            decision=SafetyDecision.EMERGENCY_STOP,
            reason=SafetyReason.HUMAN_DETECTED,
            policy_name="HumanSafetyPolicy",
        )


# ---------------------------------------------------------------------------
# Temperature Safety Policy
# ---------------------------------------------------------------------------

class TemperatureSafetyPolicy:
    """Evaluates temperature from sensor summaries.

    If temperature is not available in sensor_summaries, returns ALLOW.
    """

    def __init__(
        self,
        critical_threshold: float = 85.0,
        warning_threshold: float = 70.0,
    ) -> None:
        self.critical = critical_threshold
        self.warning = warning_threshold

    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyPolicyResult:
        temp = state.sensor_summaries.get("temperature")
        if temp is None:
            return SafetyPolicyResult(
                decision=SafetyDecision.ALLOW,
                reason=SafetyReason.TEMPERATURE_HIGH,
                policy_name="TemperatureSafetyPolicy",
            )

        if temp >= self.critical:
            return SafetyPolicyResult(
                decision=SafetyDecision.EMERGENCY_STOP,
                reason=SafetyReason.TEMPERATURE_CRITICAL,
                policy_name="TemperatureSafetyPolicy",
            )

        if temp >= self.warning:
            return SafetyPolicyResult(
                decision=SafetyDecision.PAUSE,
                reason=SafetyReason.TEMPERATURE_HIGH,
                policy_name="TemperatureSafetyPolicy",
            )

        return SafetyPolicyResult(
            decision=SafetyDecision.ALLOW,
            reason=SafetyReason.TEMPERATURE_HIGH,
            policy_name="TemperatureSafetyPolicy",
        )


# ---------------------------------------------------------------------------
# Sensor Failure Policy
# ---------------------------------------------------------------------------

class SensorFailurePolicy:
    """Evaluates individual sensor health from sensor_summaries.

    Sensors are categorized as critical or degraded. Configurable via constructor.
    If sensor_summaries is empty or missing, returns ALLOW.
    """

    def __init__(
        self,
        critical_sensors: Optional[List[str]] = None,
        degraded_sensors: Optional[List[str]] = None,
    ) -> None:
        self.critical = critical_sensors or ["lidar"]
        self.degraded = degraded_sensors or ["camera", "gps"]

    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyPolicyResult:
        summaries = state.sensor_summaries
        if not summaries:
            return SafetyPolicyResult(
                decision=SafetyDecision.ALLOW,
                reason=SafetyReason.SENSOR_FAILED,
                policy_name="SensorFailurePolicy",
            )

        for sensor in self.critical:
            if summaries.get(sensor) == "failed":
                return SafetyPolicyResult(
                    decision=SafetyDecision.CANCEL_MISSION,
                    reason=SafetyReason.SENSOR_FAILED,
                    policy_name="SensorFailurePolicy",
                )

        for sensor in self.degraded:
            if summaries.get(sensor) == "degraded":
                return SafetyPolicyResult(
                    decision=SafetyDecision.PAUSE,
                    reason=SafetyReason.SENSOR_DEGRADED,
                    policy_name="SensorFailurePolicy",
                )

        return SafetyPolicyResult(
            decision=SafetyDecision.ALLOW,
            reason=SafetyReason.SENSOR_FAILED,
            policy_name="SensorFailurePolicy",
        )


# ---------------------------------------------------------------------------
# Composite Safety Policy
# ---------------------------------------------------------------------------

DECISION_PRIORITY = {
    SafetyDecision.EMERGENCY_STOP: 5,
    SafetyDecision.CANCEL_MISSION: 4,
    SafetyDecision.PAUSE: 3,
    SafetyDecision.ALLOW: 1,
}


class CompositeSafetyPolicy:
    """Composite policy that evaluates multiple safety policies and returns
    the highest-priority decision.

    Short-circuits on EMERGENCY_STOP (terminal decision).
    Tie-breaks by registration order (first registered wins).
    """

    def __init__(self, policies: Optional[List] = None) -> None:
        self._policies: List = policies or []

    def add_policy(self, policy) -> None:
        self._policies.append(policy)

    def remove_policy(self, policy_name: str) -> None:
        self._policies = [p for p in self._policies if p.__class__.__name__ != policy_name]

    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyPolicyResult:
        best = None
        for policy in self._policies:
            result = policy.evaluate(state, context)
            if best is None or DECISION_PRIORITY.get(result.decision, 0) > DECISION_PRIORITY.get(best.decision, 0):
                best = result
            if result.decision == SafetyDecision.EMERGENCY_STOP:
                break
        return best or SafetyPolicyResult(
            decision=SafetyDecision.ALLOW,
            reason=SafetyReason.BATTERY_LOW,
            policy_name="",
        )
