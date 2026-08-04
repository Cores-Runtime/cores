from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class MemoryInfluencePolicy(ABC):
    """Translates failure/success evidence into plan score adjustments.

    Planners never see the constants behind the adjustment; they only call the
    policy. Future policies (logarithmic, Bayesian, learned, mission-specific)
    implement this same interface. A future CompositeMemoryInfluencePolicy can
    compose them under a selection strategy without touching the planner.
    """

    @abstractmethod
    def adjust_utility(self, utility: float, failures: int, successes: int) -> float:
        ...

    @abstractmethod
    def adjust_confidence(
        self, confidence: float, failures: int, successes: int
    ) -> float:
        ...


@dataclass(frozen=True)
class LinearInfluencePolicy(MemoryInfluencePolicy):
    """Linear penalty per failure and boost per success, clamped to [0, 1]."""

    failure_penalty: float = 0.15
    success_boost: float = 0.05

    def adjust_utility(self, utility: float, failures: int, successes: int) -> float:
        adjusted = (
            utility - self.failure_penalty * failures + self.success_boost * successes
        )
        return max(0.0, adjusted)

    def adjust_confidence(
        self, confidence: float, failures: int, successes: int
    ) -> float:
        adjusted = (
            confidence
            - self.failure_penalty * failures
            + self.success_boost * successes
        )
        return min(1.0, max(0.0, adjusted))
