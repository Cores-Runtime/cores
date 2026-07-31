from __future__ import annotations

from typing import List, Optional

from cores.core.memory.interface import MemoryRecord, MemoryQuery
from cores.core.memory.store import EpisodicStore, SemanticStore
from cores.core.memory.types import RecordLifecycle
from cores.core.logger.interface import LoggerStrategy
from cores.core.logger.triggers import TriggerPolicy
from cores.core.runtime_context import RuntimeContext


class Logger:
    """Internal consolidation engine.

    Orchestrates: read Episodic → compress → write Semantic → update lifecycle.
    Not a Module — called by Memory.execute() when trigger conditions are met.
    """

    def __init__(
        self,
        strategy: LoggerStrategy,
        trigger: Optional[TriggerPolicy] = None,
    ) -> None:
        self._strategy = strategy
        self._trigger = trigger

    @property
    def strategy(self) -> LoggerStrategy:
        return self._strategy

    @property
    def trigger(self) -> Optional[TriggerPolicy]:
        return self._trigger

    def should_run(self, episodic_store: EpisodicStore, context: RuntimeContext) -> bool:
        if self._trigger is None:
            return False
        return self._trigger.should_run(episodic_store, context)

    def run(self, episodic_store: EpisodicStore, semantic_store: SemanticStore) -> int:
        """Execute one consolidation pass.

        1. Read ARCHIVED records from episodic store.
        2. Compress via LoggerStrategy.
        3. Write narratives to SemanticStore.
        4. Mark source records as CONSOLIDATED.

        Returns number of narratives produced.
        """
        archived = self._fetch_archived(episodic_store)
        if not archived:
            return 0

        narratives = self._strategy.compress(archived)
        for narrative in narratives:
            semantic_store.store_narrative(narrative)

        self._mark_consolidated(episodic_store, archived)

        return len(narratives)

    def _fetch_archived(self, episodic_store: EpisodicStore) -> List[MemoryRecord]:
        """Retrieve records eligible for consolidation."""
        q = MemoryQuery(
            lifecycle=[RecordLifecycle.ARCHIVED],
            min_importance=0.0,
            max_results=100000,
        )
        result = episodic_store.query(q)
        return result.records

    def _mark_consolidated(self, episodic_store: EpisodicStore, records: List[MemoryRecord]) -> None:
        record_ids = [r.id for r in records]
        episodic_store.mark_consolidated(record_ids)
