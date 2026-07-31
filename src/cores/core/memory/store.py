from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cores.core.memory.interface import MemoryStrategy, MemoryResult

from cores.core.memory.types import (
    MemoryQuery,
    RecordLifecycle,
    NarrativeRecord,
)
from cores.core.memory.interface import MemoryRecord


class EpisodicStore:
    """Wraps a MemoryStrategy with lifecycle management.

    Lifecycle: NEW → ACTIVE → ARCHIVED → CONSOLIDATED → DISCARDED

    - NEW: just stored, not yet flushed
    - ACTIVE: flushed into the underlying strategy, actively queryable
    - ARCHIVED: low importance or old, eligible for consolidation
    - CONSOLIDATED: processed by Logger, preserved for analysis
    - DISCARDED: removed on next forget cycle
    """

    def __init__(self, strategy: MemoryStrategy) -> None:
        self._strategy = strategy
        self._pending: List[MemoryRecord] = []

    @property
    def strategy(self) -> MemoryStrategy:
        return self._strategy

    def store(self, record: MemoryRecord) -> None:
        record.lifecycle = RecordLifecycle.NEW
        self._pending.append(record)

    def store_batch(self, records: List[MemoryRecord]) -> None:
        for r in records:
            r.lifecycle = RecordLifecycle.NEW
        self._pending.extend(records)

    def query(self, q: MemoryQuery) -> MemoryResult:
        result = self._strategy.retrieve(q)
        if q.lifecycle is not None:
            filtered = [r for r in result.records if r.lifecycle in q.lifecycle]
            result.records = filtered[: q.max_results]
        return result

    def execute(self, current_cycle: int, archive_below: float = 0.0) -> Dict[str, int]:
        metrics: Dict[str, int] = {}

        # Flush pending → strategy, transition NEW → ACTIVE
        if self._pending:
            for r in self._pending:
                r.lifecycle = RecordLifecycle.ACTIVE
            self._strategy.store_batch(self._pending)
            metrics["stored"] = len(self._pending)
            self._pending.clear()
        else:
            metrics["stored"] = 0

        # Archive old/low-importance records: ACTIVE → ARCHIVED
        if archive_below > 0.0:
            all_result = self._strategy.retrieve(MemoryQuery(min_importance=0.0, max_results=100000))
            archived_count = 0
            for r in all_result.records:
                if r.lifecycle == RecordLifecycle.ACTIVE and r.importance < archive_below:
                    r.lifecycle = RecordLifecycle.ARCHIVED
                    archived_count += 1
            metrics["archived"] = archived_count

        # Forget low-importance records
        forgotten = self._strategy.forget(current_cycle)
        metrics["forgotten"] = forgotten
        metrics["size"] = self._strategy.size
        return metrics

    def mark_consolidated(self, record_ids: List[str]) -> None:
        """Called by Logger after compression. ARCHIVED → CONSOLIDATED."""
        from cores.core.memory.interface import MemoryQuery as MQ

        target = set(record_ids)
        result = self._strategy.retrieve(
            MQ(memory_types=None, min_importance=0.0, max_results=100000)
        )
        for r in result.records:
            if r.id in target and r.lifecycle == RecordLifecycle.ARCHIVED:
                r.lifecycle = RecordLifecycle.CONSOLIDATED

    @property
    def size(self) -> int:
        return self._strategy.size

    @property
    def pending_count(self) -> int:
        return len(self._pending)


class SemanticStore:
    """Holds compressed knowledge: narratives, facts, confidence models.

    No interchangeable strategies — dict-backed for simplicity.
    """

    def __init__(self) -> None:
        self._narratives: Dict[str, NarrativeRecord] = {}
        self._facts: Dict[str, Any] = {}
        self._confidence: Dict[str, float] = {}

    # ---- Narratives ----

    def store_narrative(self, narrative: NarrativeRecord) -> None:
        self._narratives[narrative.id] = narrative

    def get_narrative(self, narrative_id: str) -> Optional[NarrativeRecord]:
        return self._narratives.get(narrative_id)

    def query_narratives(self, topic: Optional[str] = None, limit: int = 10) -> List[NarrativeRecord]:
        matched = list(self._narratives.values())
        if topic:
            matched = [n for n in matched if topic.lower() in n.topic.lower()]
        matched.sort(key=lambda n: n.confidence, reverse=True)
        return matched[:limit]

    # ---- Facts ----

    def store_fact(self, key: str, value: Any) -> None:
        self._facts[key] = value

    def get_fact(self, key: str) -> Optional[Any]:
        return self._facts.get(key)

    @property
    def facts(self) -> Dict[str, Any]:
        return dict(self._facts)

    # ---- Confidence ----

    def set_confidence(self, key: str, value: float) -> None:
        self._confidence[key] = value

    def get_confidence(self, key: str) -> float:
        return self._confidence.get(key, 0.0)

    @property
    def confidence_models(self) -> Dict[str, float]:
        return dict(self._confidence)

    # ---- Query ----

    def query(self, q: MemoryQuery) -> List[NarrativeRecord]:
        matched: List[NarrativeRecord] = []
        for n in self._narratives.values():
            if q.memory_types and n.memory_type not in q.memory_types:
                continue
            if q.min_importance > 0 and n.confidence < q.min_importance:
                continue
            if q.topic and q.topic.lower() not in n.topic.lower():
                continue
            matched.append(n)
        matched.sort(key=lambda n: n.confidence, reverse=True)
        return matched[: q.max_results]

    @property
    def narrative_count(self) -> int:
        return len(self._narratives)

    def clear(self) -> None:
        self._narratives.clear()
        self._facts.clear()
        self._confidence.clear()
