from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from cores.core.memory.types import NarrativeRecord
from cores.core.memory.interface import MemoryRecord


class LoggerStrategy(ABC):
    """A strategy for compressing episodic records into semantic narratives."""

    @abstractmethod
    def compress(self, records: List[MemoryRecord]) -> List[NarrativeRecord]:
        """Convert episodic records into one or more NarrativeRecords."""
