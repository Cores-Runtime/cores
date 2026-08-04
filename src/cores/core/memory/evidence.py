from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class FailureEvidence:
    action: str
    count: int
    latest_cycle: int
    mean_importance: float


@dataclass(frozen=True)
class SuccessEvidence:
    action: str
    count: int
    latest_cycle: int
    mean_importance: float


@dataclass(frozen=True)
class NarrativeEvidence:
    topic: str
    confidence: float
    count: int


@dataclass(frozen=True)
class EvidenceSet:
    failures: Tuple[FailureEvidence, ...] = ()
    successes: Tuple[SuccessEvidence, ...] = ()
    narratives: Tuple[NarrativeEvidence, ...] = ()

    def failure_count(self, action: str) -> int:
        for e in self.failures:
            if e.action == action:
                return e.count
        return 0

    def success_count(self, action: str) -> int:
        for e in self.successes:
            if e.action == action:
                return e.count
        return 0

    def narrative_for_topic(self, topic: str) -> Optional[NarrativeEvidence]:
        for n in self.narratives:
            if n.topic == topic:
                return n
        return None
