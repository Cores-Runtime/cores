from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from cores.interfaces.module import Module, ModuleResult
from cores.core.robot_state import RobotState

if TYPE_CHECKING:
    from cores.core.runtime_context import RuntimeContext
    from cores.core.memory.store import EpisodicStore, SemanticStore

from cores.core.memory.types import (
    MemoryType,
    RecordLifecycle,
    MemoryQuery,
    NarrativeRecord,
)
from cores.core.memory.evidence import (
    EvidenceSet,
    FailureEvidence,
    SuccessEvidence,
    NarrativeEvidence,
)


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
    record_type: MemoryType = MemoryType.OBSERVATION
    lifecycle: RecordLifecycle = RecordLifecycle.NEW
    metadata: Dict[str, Any] = field(default_factory=dict)


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

    Composes EpisodicStore + SemanticStore + Logger.

    EpisodicStore wraps a MemoryStrategy (FIFO / Priority / TimeDecay / EpisodicStrategy)
    for raw record storage. SemanticStore holds compressed narratives and facts.
    Logger consolidates episodic records into semantic narratives when its trigger fires.

    Planners access memory through the PlanningContext, calling query() or ask().
    """

    def __init__(
        self,
        episodic_store: Optional["EpisodicStore"] = None,
        semantic_store: Optional["SemanticStore"] = None,
        logger: Optional[Any] = None,
        archive_below: float = 0.3,
        name: str = "memory",
    ) -> None:
        super().__init__(name)
        if episodic_store is None:
            from cores.core.memory.strategies.priority_memory import PriorityMemoryStrategy
            from cores.core.memory.store import EpisodicStore as ES
            episodic_store = ES(PriorityMemoryStrategy())

        from cores.core.memory.store import SemanticStore as SS
        self._episodic = episodic_store
        self._semantic = semantic_store or SS()
        self._logger = logger or self._default_logger()
        self._archive_below = archive_below
        self._pending_store: List[MemoryRecord] = []

    @staticmethod
    def _default_logger() -> Any:
        """Build a Logger with a sensible default trigger."""
        from cores.core.logger.logger import Logger
        from cores.core.logger.spsca import SPSCALogger
        from cores.core.logger.triggers import CountTrigger

        return Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=50))

    @property
    def episodic(self) -> Any:
        return self._episodic

    @property
    def semantic(self) -> Any:
        return self._semantic

    @property
    def logger(self) -> Any:
        return self._logger

    @property
    def strategy(self) -> Any:
        return self._episodic.strategy

    def store(self, record: MemoryRecord) -> None:
        """Queue a record for storage on the next cycle."""
        record.lifecycle = RecordLifecycle.NEW
        self._pending_store.append(record)

    def store_batch(self, records: List[MemoryRecord]) -> None:
        """Queue multiple records for storage on the next cycle."""
        for r in records:
            r.lifecycle = RecordLifecycle.NEW
        self._pending_store.extend(records)

    def ask(self, query: MemoryQuery) -> MemoryResult:
        """Query memory. Called by Planners during their cycle."""
        return self._episodic.query(query)

    def query(self, q: MemoryQuery) -> MemoryResult:
        """Structured query — merges EpisodicStore + SemanticStore results."""
        episodic_result = self._episodic.query(q)
        semantic_records = self._semantic.query(q)

        merged = list(episodic_result.records) + list(semantic_records)
        merged.sort(key=lambda r: r.importance if hasattr(r, 'importance') else getattr(r, 'confidence', 0.5), reverse=True)
        merged = merged[: q.max_results]

        return MemoryResult(records=merged, query=q)

    def evidence(self, query: Optional[MemoryQuery] = None) -> EvidenceSet:
        """Aggregate stored outcomes and narratives into planning evidence.

        Planners consume evidence, never raw records. Memory owns the record
        format, so it can change internally without touching Planning.
        """
        q = query or MemoryQuery()
        outcomes = self._episodic.query(
            MemoryQuery(
                memory_types=[MemoryType.OUTCOME],
                location=q.location,
                action=q.action,
                min_importance=q.min_importance,
                max_age_cycles=q.max_age_cycles,
                max_results=100000,
            )
        ).records
        narratives = self._semantic.query(
            MemoryQuery(
                memory_types=[MemoryType.NARRATIVE],
                topic=q.topic,
                min_importance=q.min_importance,
                max_results=100000,
            )
        )

        failures: Dict[str, List[MemoryRecord]] = {}
        successes: Dict[str, List[MemoryRecord]] = {}
        for r in outcomes:
            content = r.content if isinstance(r.content, dict) else {}
            action = content.get("action")
            if not action:
                continue
            if q.action is not None and action != q.action:
                continue
            if q.location is not None and content.get("location") != q.location:
                continue
            result = str(content.get("result", "")).upper()
            if result == "FAILURE":
                failures.setdefault(action, []).append(r)
            elif result == "SUCCESS":
                successes.setdefault(action, []).append(r)

        failure_evidence = tuple(
            _outcome_evidence(action, records, FailureEvidence)
            for action, records in sorted(failures.items())
        )
        success_evidence = tuple(
            _outcome_evidence(action, records, SuccessEvidence)
            for action, records in sorted(successes.items())
        )

        by_topic: Dict[str, List[NarrativeRecord]] = {}
        for n in narratives:
            by_topic.setdefault(n.topic or "unknown", []).append(n)
        narrative_evidence = tuple(
            NarrativeEvidence(
                topic=topic,
                confidence=max(r.confidence for r in records),
                count=len(records),
            )
            for topic, records in sorted(by_topic.items())
        )

        return EvidenceSet(
            failures=failure_evidence,
            successes=success_evidence,
            narratives=narrative_evidence,
        )

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        """Run the memory cognitive loop for one cycle.

        1. Store pending records → EpisodicStore
        2. EpisodicStore lifecycle (flush NEW→ACTIVE, archive, forget)
        3. Logger consolidation (if trigger fires)
        4. Publish metrics
        """
        metrics: Dict[str, Any] = {}

        # 1. Flush pending stores into EpisodicStore
        if self._pending_store:
            self._episodic.store_batch(self._pending_store)
            metrics["stored"] = len(self._pending_store)
            self._pending_store.clear()
        else:
            metrics["stored"] = 0

        # 2. EpisodicStore lifecycle pass (archives records below archive_below)
        ep_metrics = self._episodic.execute(
            context.cycle_count, archive_below=self._archive_below
        )
        metrics.update(ep_metrics)

        # 3. Logger consolidation (if trigger fires)
        if self._logger is not None and self._logger.should_run(self._episodic, context):
            narratives_produced = self._logger.run(self._episodic, self._semantic)
            metrics["narratives_produced"] = narratives_produced
        else:
            metrics["narratives_produced"] = 0

        # 4. Publish metrics
        mem_metrics = self._episodic.strategy.metrics
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


def make_record_id(content: Any, cycle: int) -> str:
    """Generate a deterministic record id from content and cycle number."""
    raw = json.dumps(content, sort_keys=True, default=str) + str(cycle)
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _outcome_evidence(
    action: str, records: List[MemoryRecord], evidence_cls: type
) -> Any:
    count = len(records)
    latest = max(r.cycle for r in records)
    mean = sum(r.importance for r in records) / count
    return evidence_cls(
        action=action,
        count=count,
        latest_cycle=latest,
        mean_importance=mean,
    )
