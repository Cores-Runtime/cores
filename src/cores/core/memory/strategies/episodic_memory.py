import math
from typing import Dict, List, Optional, Set

from cores.core.memory.interface import (
    MemoryRecord,
    MemoryQuery,
    MemoryResult,
    MemoryMetrics,
    MemoryStrategy,
)


class Episode:
    """A group of related records."""

    def __init__(
        self,
        episode_id: str,
        start_cycle: int,
        records: Optional[List[MemoryRecord]] = None,
    ) -> None:
        self.episode_id = episode_id
        self.start_cycle = start_cycle
        self.end_cycle = start_cycle
        self.records: List[MemoryRecord] = records or []
        self.importance: float = 0.0
        self.access_count: int = 0

    def add_record(self, record: MemoryRecord) -> None:
        self.records.append(record)
        if record.cycle > self.end_cycle:
            self.end_cycle = record.cycle
        self.importance = max(self.importance, record.importance)

    @property
    def duration(self) -> int:
        return self.end_cycle - self.start_cycle

    @property
    def record_ids(self) -> Set[str]:
        return {r.id for r in self.records}


class EpisodicMemoryStrategy(MemoryStrategy):
    """Episodic memory.

    Groups records into episodes. Each episode represents a sequence of
    related events. An episode boundary is created when there is a gap
    of more than `gap_threshold` cycles between consecutive records.
    """

    def __init__(
        self,
        gap_threshold: int = 5,
        max_episodes: int = 100,
    ) -> None:
        self._gap_threshold = gap_threshold
        self._max_episodes = max_episodes
        self._episodes: Dict[str, Episode] = {}
        self._episode_order: List[str] = []
        self._current_episode_id: Optional[str] = None
        self._retrieval_count = 0
        self._insertion_count = 0
        self._forgetting_count = 0

    def store(self, record: MemoryRecord) -> None:
        self._insertion_count += 1
        if self._current_episode_id is not None:
            current = self._episodes[self._current_episode_id]
            gap = record.cycle - current.end_cycle
            if gap > self._gap_threshold:
                self._current_episode_id = None

        if self._current_episode_id is None:
            episode_id = f"ep_{record.cycle}_{record.id[:8]}"
            ep = Episode(episode_id, record.cycle)
            self._episodes[episode_id] = ep
            self._episode_order.append(episode_id)
            self._current_episode_id = episode_id

        self._episodes[self._current_episode_id].add_record(record)
        self._enforce_limit()

    def store_batch(self, records: List[MemoryRecord]) -> None:
        for record in records:
            self.store(record)

    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        self._retrieval_count += 1
        all_records: List[MemoryRecord] = []
        for ep in self._episodes.values():
            for record in ep.records:
                if self._matches(record, query):
                    all_records.append(record)

        all_records.sort(key=lambda r: r.importance, reverse=True)
        return MemoryResult(records=all_records[: query.limit], query=query)

    def forget(self, current_cycle: int) -> int:
        before = self.size
        to_remove: List[str] = []
        for eid, ep in self._episodes.items():
            age = current_cycle - ep.end_cycle
            decayed = ep.importance * math.pow(0.99, max(0, age))
            if decayed < 0.05:
                to_remove.append(eid)
        for eid in to_remove:
            del self._episodes[eid]
            if eid in self._episode_order:
                self._episode_order.remove(eid)
        if self._current_episode_id in to_remove:
            self._current_episode_id = self._episode_order[-1] if self._episode_order else None
        removed = before - self.size
        self._forgetting_count += removed
        return removed

    def clear(self) -> None:
        self._episodes.clear()
        self._episode_order.clear()
        self._current_episode_id = None

    @property
    def size(self) -> int:
        return sum(len(ep.records) for ep in self._episodes.values())

    @property
    def metrics(self) -> MemoryMetrics:
        return MemoryMetrics(
            total_records=self.size,
            retrieval_count=self._retrieval_count,
            insertion_count=self._insertion_count,
            forgetting_count=self._forgetting_count,
            strategy_name="episodic",
        )

    def _enforce_limit(self) -> None:
        while len(self._episodes) > self._max_episodes:
            oldest = self._episode_order.pop(0)
            del self._episodes[oldest]

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
