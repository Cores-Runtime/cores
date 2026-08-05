from __future__ import annotations

from typing import Optional

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.safety_supervisor.types import (
    SafetyDecision,
    SafetyReason,
    SafetyResult,
)
from cores.core.safety_supervisor.policies import (
    CompositeSafetyPolicy,
    BatterySafetyPolicy,
    CollisionSafetyPolicy,
    HumanSafetyPolicy,
    TemperatureSafetyPolicy,
    SensorFailurePolicy,
)


class SafetySupervisor:
    """Safety Supervisor evaluates the current robot state and returns a safety decision.

    Safety is the highest decision-making layer in the runtime. It never plans,
    schedules, executes, or estimates state. It only decides whether the current
    behavior is safe.

    The SafetySupervisor owns a CompositeSafetyPolicy which holds the list of
    individual policies. The register_policy and remove_policy methods are
    convenience forwarding methods; the real owner of the policy list is the
    CompositeSafetyPolicy.
    """

    def __init__(self, composite_policy: Optional[CompositeSafetyPolicy] = None) -> None:
        if composite_policy is not None:
            self._composite = composite_policy
        else:
            self._composite = CompositeSafetyPolicy()
            self._register_default_policies()
        self._last_result: Optional[SafetyResult] = None

    def _register_default_policies(self) -> None:
        """Register the 5 default safety policies."""
        self._composite.add_policy(BatterySafetyPolicy())
        self._composite.add_policy(CollisionSafetyPolicy())
        self._composite.add_policy(HumanSafetyPolicy())
        self._composite.add_policy(TemperatureSafetyPolicy())
        self._composite.add_policy(SensorFailurePolicy())

    @property
    def composite_policy(self) -> CompositeSafetyPolicy:
        """Return the composite policy that owns the policy list."""
        return self._composite

    # ------------------------------------------------------------------
    # Convenience forwarding methods (real owner is CompositeSafetyPolicy)
    # ------------------------------------------------------------------

    def register_policy(self, policy) -> None:
        """Register a safety policy. Convenience method that forwards to
        CompositeSafetyPolicy.add_policy."""
        self._composite.add_policy(policy)

    def remove_policy(self, policy_name: str) -> None:
        """Remove a safety policy by class name. Convenience method that
        forwards to CompositeSafetyPolicy.remove_policy."""
        self._composite.remove_policy(policy_name)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def evaluate(self, state: RobotState, context: RuntimeContext) -> SafetyResult:
        """Evaluate the current state against all registered safety policies.

        Returns a SafetyResult with the highest-priority decision.
        """
        policy_result = self._composite.evaluate(state, context)
        self._last_result = SafetyResult(
            decision=policy_result.decision,
            reason=policy_result.reason,
            triggering_policy=policy_result.policy_name,
        )
        return self._last_result

    def current_decision(self) -> Optional[SafetyDecision]:
        """Return the most recent safety decision, or None if not yet evaluated."""
        return self._last_result.decision if self._last_result else None

    def current_reason(self) -> Optional[SafetyReason]:
        """Return the most recent safety reason, or None if not yet evaluated."""
        return self._last_result.reason if self._last_result else None
