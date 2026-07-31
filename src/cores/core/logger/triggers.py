from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from cores.core.memory.store import EpisodicStore
from cores.core.runtime_context import RuntimeContext


class TriggerPolicy(ABC):
    """Determines whether the Narrator should run."""

    @abstractmethod
    def should_run(self, episodic_store: EpisodicStore, context: RuntimeContext) -> bool:
        ...


class CapacityTrigger(TriggerPolicy):
    """Runs narrator when episodic store exceeds a capacity threshold.

    Uses episodic_store.size directly. The threshold is an absolute count.
    """

    def __init__(self, threshold: int = 100) -> None:
        self._threshold = threshold

    def should_run(self, episodic_store: EpisodicStore, context: RuntimeContext) -> bool:
        return episodic_store.size >= self._threshold


class CountTrigger(TriggerPolicy):
    """Runs narrator after N new records have been added since last run."""

    def __init__(self, count: int = 100) -> None:
        self._count = count
        self._last_size = 0

    def should_run(self, episodic_store: EpisodicStore, context: RuntimeContext) -> bool:
        current = episodic_store.size
        new_records = current - self._last_size
        if new_records >= self._count:
            self._last_size = current
            return True
        return False


class IdleTrigger(TriggerPolicy):
    """Runs narrator when the robot has been idle for N cycles."""

    def __init__(self, idle_cycles: int = 50) -> None:
        self._idle_cycles = idle_cycles
        self._last_active_cycle = 0

    def should_run(self, episodic_store: EpisodicStore, context: RuntimeContext) -> bool:
        if context.cycle_count - self._last_active_cycle >= self._idle_cycles:
            self._last_active_cycle = context.cycle_count
            return True
        return False


class CompositeTrigger(TriggerPolicy):
    """Combines multiple triggers with AND/OR logic."""

    def __init__(self, triggers: List[TriggerPolicy], mode: str = "any") -> None:
        self._triggers = triggers
        self._mode = mode

    def should_run(self, episodic_store: EpisodicStore, context: RuntimeContext) -> bool:
        if not self._triggers:
            return False
        results = [t.should_run(episodic_store, context) for t in self._triggers]
        if self._mode == "all":
            return all(results)
        return any(results)
