from typing import Dict, List

from cores.core.memory.interface import (
    MemoryRecord,
    MemoryQuery,
    MemoryResult,
    MemoryMetrics,
    MemoryStrategy,
)


class FIFOMemoryStrategy(MemoryStrategy):
    """First-in, first-out memory.

    Stores records in insertion order. When the max size is reached,
    the oldest records are dropped first. Importance and content are ignored.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max_size
        self._records: Dict[str, MemoryRecord] = {}
        self._order: List[str] = []
        self._retrieval_count = 0
        self._insertion_count = 0
        self._forgetting_count = 0

    def store(self, record: MemoryRecord) -> None:
        if record.id in self._records:
            self._order.remove(record.id)
        self._records[record.id] = record
        self._order.append(record.id)
        self._insertion_count += 1
        self._enforce_limit()

    def store_batch(self, records: List[MemoryRecord]) -> None:
        for record in records:
            self.store(record)

    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        matched: List[MemoryRecord] = []
        for rid in reversed(self._order):
            record = self._records[rid]
            if self._matches(record, query):
                matched.append(record)
                if len(matched) >= query.limit:
                    break
        self._retrieval_count += 1
        return MemoryResult(records=matched, query=query)

    def forget(self, current_cycle: int) -> int:
        before = self.size
        overflow = self.size - self._max_size
        if overflow > 0:
            to_remove = self._order[:overflow]
            for rid in to_remove:
                del self._records[rid]
            self._order = self._order[overflow:]
        removed = before - self.size
        self._forgetting_count += removed
        return removed

    def clear(self) -> None:
        self._records.clear()
        self._order.clear()

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def metrics(self) -> MemoryMetrics:
        return MemoryMetrics(
            total_records=self.size,
            retrieval_count=self._retrieval_count,
            insertion_count=self._insertion_count,
            forgetting_count=self._forgetting_count,
            strategy_name="fifo",
        )

    def _enforce_limit(self) -> None:
        while self.size > self._max_size:
            oldest = self._order.pop(0)
            del self._records[oldest]

    def _matches(self, record: MemoryRecord, query: MemoryQuery) -> bool:
        if record.importance < query.min_importance:
            return False
        if query.record_types and record.record_type not in query.record_types:
            return False
        if query.max_age_cycles is not None:
            age = abs(record.cycle)
            if age > query.max_age_cycles:
                return False
        return True
