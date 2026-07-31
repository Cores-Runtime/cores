"""Integration tests for the Logger consolidation pipeline."""

from cores.core.memory import (
    MemoryRecord,
    MemoryType,
    EpisodicStore,
    SemanticStore,
)
from cores.core.memory.strategies.fifo_memory import FIFOMemoryStrategy
from cores.core.logger import (
    Logger,
    SPSCALogger,
    CountTrigger,
)
from cores.core.runtime_context import RuntimeContext


def make_episodic_record(
    rid: str,
    content: dict,
    cycle: int,
) -> MemoryRecord:
    return MemoryRecord(
        id=rid,
        content=content,
        cycle=cycle,
        importance=0.5,
        record_type=MemoryType.OBSERVATION,
    )


class TestLoggerPipeline:
    def _setup(self, count: int = 5) -> tuple:
        """Store records, flush to ACTIVE, then archive them for logger."""
        episodic = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        semantic = SemanticStore()
        for i in range(count):
            r = make_episodic_record(f"r{i}", {"action": "walk", "step": i}, cycle=i)
            episodic.store(r)
        episodic.execute(0, archive_below=0.6)
        return episodic, semantic

    def test_logger_produces_narratives(self):
        episodic, semantic = self._setup(10)

        logger = Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=5))
        ctx = RuntimeContext()
        assert logger.should_run(episodic, ctx) is True

        produced = logger.run(episodic, semantic)
        assert produced > 0
        assert semantic.narrative_count == produced

    def test_logger_does_not_run_without_trigger(self):
        episodic, semantic = self._setup(10)

        logger = Logger(strategy=SPSCALogger())
        ctx = RuntimeContext()
        assert logger.should_run(episodic, ctx) is False

    def test_logger_empty_episodic(self):
        episodic = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        semantic = SemanticStore()
        logger = Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=1))
        produced = logger.run(episodic, semantic)
        assert produced == 0

    def test_semantic_store_holds_narratives(self):
        episodic, semantic = self._setup(5)

        logger = Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=1))
        logger.run(episodic, semantic)

        narratives = semantic.query_narratives()
        assert len(narratives) > 0
        for n in narratives:
            assert n.memory_type == MemoryType.NARRATIVE

    def test_logger_metrics(self):
        episodic, semantic = self._setup(10)

        logger = Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=5))
        ctx = RuntimeContext()
        assert logger.should_run(episodic, ctx) is True

        narratives_produced = logger.run(episodic, semantic)
        assert narratives_produced > 0
        assert len(semantic.query_narratives()) == narratives_produced
