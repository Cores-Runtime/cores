from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cores.interfaces.module import Module, ModuleResult
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class MemoryRecord:
    """A single stored item in memory."""

    id: str
    content: Any
    cycle: int
    importance: float = 0.5
    access_count: int = 0
    last_accessed_cycle: int = 0
    record_type: str = "generic"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryQuery:
    """A request to retrieve records from memory."""

    query: str = ""
    record_types: Optional[List[str]] = None
    min_importance: float = 0.0
    max_age_cycles: Optional[int] = None
    limit: int = 10


@dataclass
class MemoryResult:
    """The result of a memory query."""

    records: List[MemoryRecord]
    query: MemoryQuery = field(default_factory=MemoryQuery)
    retrieval_time_ms: float = 0.0


@dataclass
class MemoryMetrics:
    """Per-strategy statistics."""

    total_records: int = 0
    retrieval_count: int = 0
    insertion_count: int = 0
    forgetting_count: int = 0
    strategy_name: str = ""


# ---------------------------------------------------------------------------
# MemoryStrategy interface
# ---------------------------------------------------------------------------


class MemoryStrategy(ABC):
    """Pluggable strategy for storing, retrieving, and forgetting records."""

    @abstractmethod
    def store(self, record: MemoryRecord) -> None:
        """Store a single record."""

    @abstractmethod
    def store_batch(self, records: List[MemoryRecord]) -> None:
        """Store multiple records."""

    @abstractmethod
    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve records matching the query."""

    @abstractmethod
    def forget(self, current_cycle: int) -> int:
        """Remove records that should be forgotten. Returns count removed."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all records."""

    @property
    @abstractmethod
    def size(self) -> int:
        """Number of records currently stored."""

    @property
    @abstractmethod
    def metrics(self) -> MemoryMetrics:
        """Current strategy statistics."""


# ---------------------------------------------------------------------------
# Memory cognitive node
# ---------------------------------------------------------------------------


class Memory(Module):
    """The Memory cognitive node.

    Runs after StateEstimation each cycle. Stores current observations,
    consolidates important records, and forgets stale ones.

    Planners access memory through the PlanningContext.
    """

    def __init__(
        self,
        strategy: MemoryStrategy,
        name: str = "memory",
    ) -> None:
        super().__init__(name)
        self._strategy = strategy
        self._pending_store: List[MemoryRecord] = []

    @property
    def strategy(self) -> MemoryStrategy:
        return self._strategy

    def store(self, record: MemoryRecord) -> None:
        """Queue a record for storage on the next cycle."""
        self._pending_store.append(record)

    def store_batch(self, records: List[MemoryRecord]) -> None:
        """Queue multiple records for storage on the next cycle."""
        self._pending_store.extend(records)

    def ask(self, query: MemoryQuery) -> MemoryResult:
        """Query memory. Called by Planners during their cycle."""
        return self._strategy.retrieve(query)

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        """Run the memory cognitive loop for one cycle.

        1. Flush pending stores into the strategy.
        2. Consolidate: boost importance for frequently accessed records.
        3. Forget records below the importance threshold.
        4. Publish metrics.
        """
        metrics: Dict[str, Any] = {}

        # 1. Store pending records
        if self._pending_store:
            self._strategy.store_batch(self._pending_store)
            metrics["stored"] = len(self._pending_store)
            self._pending_store.clear()
        else:
            metrics["stored"] = 0

        # 2. Consolidate: boost importance for frequently accessed records
        consolidated = self._consolidate(context.cycle_count)
        metrics["consolidated"] = consolidated

        # 3. Forget
        forgotten = self._strategy.forget(context.cycle_count)
        metrics["forgotten"] = forgotten

        # 4. Publish metrics
        mem_metrics = self._strategy.metrics
        metrics["total_records"] = mem_metrics.total_records
        metrics["strategy"] = mem_metrics.strategy_name
        metrics["retrieval_count"] = mem_metrics.retrieval_count
        metrics["insertion_count"] = mem_metrics.insertion_count

        return ModuleResult(
            module_name=self.name,
            status="SUCCESS",
            metrics=metrics,
            execution_time_ms=0.0,
        )

    def _consolidate(self, current_cycle: int) -> int:
        """Boost importance for records accessed within the last cycle."""
        count = 0
        all_records: List[MemoryRecord] = []

        result = self._strategy.retrieve(
            MemoryQuery(query="", min_importance=0.0, limit=100000)
        )
        all_records = result.records

        for record in all_records:
            if record.last_accessed_cycle == current_cycle:
                record.importance = min(1.0, record.importance + 0.05)
                count += 1

        return count


def make_record_id(content: Any, cycle: int) -> str:
    """Generate a deterministic record id from content and cycle number."""
    raw = json.dumps(content, sort_keys=True, default=str) + str(cycle)
    return hashlib.md5(raw.encode()).hexdigest()[:16]
