import math
from typing import Dict, List

from cores.core.memory.interface import (
    MemoryRecord,
    MemoryQuery,
    MemoryResult,
    MemoryMetrics,
    MemoryStrategy,
)


class TimeDecayMemoryStrategy(MemoryStrategy):
    """Time-decay memory.

    Each record has an importance that decays by a fixed fraction every cycle
    since it was last accessed. Records below the forget threshold are removed
    on the next forget() call.
    """

    def __init__(
        self,
        decay_rate: float = 0.01,
        forget_threshold: float = 0.1,
        max_size: int = 1000,
    ) -> None:
        self._decay_rate = decay_rate
        self._forget_threshold = forget_threshold
        self._max_size = max_size
        self._records: Dict[str, MemoryRecord] = {}
        self._retrieval_count = 0
        self._insertion_count = 0
        self._forgetting_count = 0

    def store(self, record: MemoryRecord) -> None:
        self._records[record.id] = record
        self._insertion_count += 1
        self._enforce_limit()

    def store_batch(self, records: List[MemoryRecord]) -> None:
        for record in records:
            self.store(record)

    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        self._retrieval_count += 1
        matched: List[MemoryRecord] = []
        for record in self._records.values():
            if self._matches(record, query):
                matched.append(record)
                if len(matched) >= query.limit:
                    break
        return MemoryResult(records=matched, query=query)

    def forget(self, current_cycle: int) -> int:
        before = self.size
        to_remove: List[str] = []

        for rid, record in self._records.items():
            age = max(0, current_cycle - record.last_accessed_cycle)
            decayed = record.importance * math.pow(1.0 - self._decay_rate, age)
            if decayed < self._forget_threshold:
                to_remove.append(rid)

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
            strategy_name="time_decay",
        )

    def _enforce_limit(self) -> None:
        while self.size > self._max_size:
            oldest_id = min(self._records.keys(), key=lambda rid: self._records[rid].cycle)
            del self._records[oldest_id]

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
