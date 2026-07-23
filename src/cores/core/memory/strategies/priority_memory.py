from typing import Dict, List

from cores.core.memory.interface import (
    MemoryRecord,
    MemoryQuery,
    MemoryResult,
    MemoryMetrics,
    MemoryStrategy,
)


class PriorityMemoryStrategy(MemoryStrategy):
    """Priority-based memory.

    Keeps only the most important records up to max_size. When full,
    the lowest-importance record is dropped. Importance can be boosted
    by access frequency.
    """

    def __init__(self, max_size: int = 1000, forget_below: float = 0.05) -> None:
        self._max_size = max_size
        self._forget_below = forget_below
        self._records: Dict[str, MemoryRecord] = {}
        self._retrieval_count = 0
        self._insertion_count = 0
        self._forgetting_count = 0

    def store(self, record: MemoryRecord) -> None:
        if record.id in self._records:
            existing = self._records[record.id]
            if record.importance > existing.importance:
                existing.importance = record.importance
            existing.content = record.content
            existing.cycle = record.cycle
            existing.metadata.update(record.metadata)
        else:
            self._records[record.id] = record
            self._insertion_count += 1
        self._enforce_limit()

    def store_batch(self, records: List[MemoryRecord]) -> None:
        for record in records:
            self.store(record)

    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        self._retrieval_count += 1
        matched: List[MemoryRecord] = []
        for record in sorted(
            self._records.values(),
            key=lambda r: r.importance,
            reverse=True,
        ):
            if self._matches(record, query):
                matched.append(record)
                if len(matched) >= query.limit:
                    break
        return MemoryResult(records=matched, query=query)

    def forget(self, current_cycle: int) -> int:
        before = self.size
        to_remove: List[str] = [
            rid
            for rid, record in self._records.items()
            if record.importance < self._forget_below
        ]
        for rid in to_remove:
            del self._records[rid]
        removed = before - self.size
        self._forgetting_count += removed
        return removed

    def clear(self) -> None:
        self._records.clear()

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
            strategy_name="priority",
        )

    def _enforce_limit(self) -> None:
        while self.size > self._max_size:
            lowest_id = min(
                self._records.keys(),
                key=lambda rid: self._records[rid].importance,
            )
            del self._records[lowest_id]

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
