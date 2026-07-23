import math

from cores.core.memory import (
    MemoryRecord,
    MemoryQuery,
    MemoryResult,
    Memory,
    FIFOMemoryStrategy,
    TimeDecayMemoryStrategy,
    PriorityMemoryStrategy,
    EpisodicMemoryStrategy,
    SPSCAMemoryStrategy,
    make_record_id,
)
from cores.core.memory.semantic_pointers import SemanticPointer, encode_content
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


# =========================================================================
# Data types
# =========================================================================


class TestMemoryRecord:
    def test_default_creation(self):
        record = MemoryRecord(id="r1", content={"x": 1}, cycle=0)
        assert record.id == "r1"
        assert record.content == {"x": 1}
        assert record.cycle == 0
        assert record.importance == 0.5
        assert record.access_count == 0
        assert record.record_type == "generic"

    def test_with_metadata(self):
        record = MemoryRecord(
            id="r2", content="hello", cycle=5,
            importance=0.9, record_type="episodic",
            metadata={"source": "camera"},
        )
        assert record.importance == 0.9
        assert record.record_type == "episodic"
        assert record.metadata["source"] == "camera"


class TestMemoryQuery:
    def test_default_query(self):
        q = MemoryQuery()
        assert q.query == ""
        assert q.min_importance == 0.0
        assert q.limit == 10

    def test_filtered_query(self):
        q = MemoryQuery(
            query="obstacle",
            record_types=["episodic"],
            min_importance=0.5,
            max_age_cycles=100,
            limit=5,
        )
        assert q.record_types == ["episodic"]
        assert q.max_age_cycles == 100
        assert q.limit == 5


class TestMemoryResult:
    def test_creation(self):
        records = [MemoryRecord(id="r1", content="a", cycle=0)]
        result = MemoryResult(records=records)
        assert len(result.records) == 1


class TestMakeRecordId:
    def test_deterministic(self):
        a = make_record_id({"key": "value"}, 1)
        b = make_record_id({"key": "value"}, 1)
        assert a == b

    def test_different_cycle(self):
        a = make_record_id({"key": "value"}, 1)
        b = make_record_id({"key": "value"}, 2)
        assert a != b


# =========================================================================
# FIFO Memory Strategy
# =========================================================================


class TestFIFOMemoryStrategy:
    def test_store_and_retrieve(self):
        s = FIFOMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="first", cycle=0))
        s.store(MemoryRecord(id="r2", content="second", cycle=1))
        result = s.retrieve(MemoryQuery(limit=10))
        assert len(result.records) == 2
        assert result.records[0].id == "r2"

    def test_fifo_eviction(self):
        s = FIFOMemoryStrategy(max_size=3)
        for i in range(5):
            s.store(MemoryRecord(id=f"r{i}", content=i, cycle=i))
        assert s.size == 3
        ids = {r.id for r in s.retrieve(MemoryQuery(limit=10)).records}
        assert "r0" not in ids
        assert "r4" in ids

    def test_forget_noop_when_under_limit(self):
        s = FIFOMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        forgotten = s.forget(current_cycle=10)
        assert forgotten == 0
        assert s.size == 1

    def test_clear(self):
        s = FIFOMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        s.clear()
        assert s.size == 0

    def test_metrics(self):
        s = FIFOMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        s.retrieve(MemoryQuery())
        m = s.metrics
        assert m.strategy_name == "fifo"
        assert m.total_records == 1
        assert m.retrieval_count == 1


# =========================================================================
# TimeDecay Memory Strategy
# =========================================================================


class TestTimeDecayMemoryStrategy:
    def test_store_and_retrieve(self):
        s = TimeDecayMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0, importance=0.9))
        result = s.retrieve(MemoryQuery(min_importance=0.5))
        assert len(result.records) == 1

    def test_filter_by_importance(self):
        s = TimeDecayMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0, importance=0.3))
        s.store(MemoryRecord(id="r2", content="b", cycle=0, importance=0.9))
        result = s.retrieve(MemoryQuery(min_importance=0.5))
        assert len(result.records) == 1
        assert result.records[0].id == "r2"

    def test_forget_decayed(self):
        s = TimeDecayMemoryStrategy(
            decay_rate=0.5, forget_threshold=0.3, max_size=10
        )
        s.store(MemoryRecord(
            id="r1", content="a", cycle=0, importance=0.9,
            last_accessed_cycle=0,
        ))
        # After 3 cycles, decayed = 0.9 * (0.5^3) = 0.1125 < 0.3
        forgotten = s.forget(current_cycle=3)
        assert forgotten == 1
        assert s.size == 0

    def test_clear(self):
        s = TimeDecayMemoryStrategy()
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        s.clear()
        assert s.size == 0


# =========================================================================
# Priority Memory Strategy
# =========================================================================


class TestPriorityMemoryStrategy:
    def test_store_and_retrieve(self):
        s = PriorityMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0, importance=0.8))
        s.store(MemoryRecord(id="r2", content="b", cycle=0, importance=0.2))
        result = s.retrieve(MemoryQuery(limit=10))
        assert result.records[0].id == "r1"

    def test_priority_eviction(self):
        s = PriorityMemoryStrategy(max_size=3, forget_below=0.01)
        s.store(MemoryRecord(id="r1", content="high", cycle=0, importance=0.9))
        s.store(MemoryRecord(id="r2", content="med", cycle=0, importance=0.5))
        s.store(MemoryRecord(id="r3", content="low", cycle=0, importance=0.1))
        s.store(MemoryRecord(id="r4", content="high2", cycle=1, importance=0.95))
        assert s.size == 3
        ids = {r.id for r in s.retrieve(MemoryQuery(limit=10)).records}
        assert "r3" not in ids

    def test_forget_below_threshold(self):
        s = PriorityMemoryStrategy(forget_below=0.3)
        s.store(MemoryRecord(id="r1", content="low", cycle=0, importance=0.1))
        s.store(MemoryRecord(id="r2", content="high", cycle=0, importance=0.9))
        forgotten = s.forget(current_cycle=0)
        assert forgotten == 1
        assert s.size == 1

    def test_merge_duplicate_id(self):
        s = PriorityMemoryStrategy(max_size=10)
        s.store(MemoryRecord(id="r1", content="old", cycle=0, importance=0.3))
        s.store(MemoryRecord(id="r1", content="new", cycle=1, importance=0.9))
        result = s.retrieve(MemoryQuery(limit=10))
        assert len(result.records) == 1
        assert result.records[0].content == "new"


# =========================================================================
# Episodic Memory Strategy
# =========================================================================


class TestEpisodicMemoryStrategy:
    def test_store_and_retrieve(self):
        s = EpisodicMemoryStrategy(gap_threshold=5, max_episodes=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        s.store(MemoryRecord(id="r2", content="b", cycle=1))
        result = s.retrieve(MemoryQuery(limit=10))
        assert len(result.records) == 2

    def test_episode_boundary(self):
        s = EpisodicMemoryStrategy(gap_threshold=3, max_episodes=10)
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        s.store(MemoryRecord(id="r2", content="b", cycle=10))
        result = s.retrieve(MemoryQuery(limit=10))
        assert len(result.records) == 2

    def test_forget_old_episodes(self):
        s = EpisodicMemoryStrategy(max_episodes=10)
        s.store(MemoryRecord(id="r1", content="old", cycle=0, importance=0.01))
        forgotten = s.forget(current_cycle=100)
        assert forgotten >= 1

    def test_max_episodes(self):
        s = EpisodicMemoryStrategy(gap_threshold=1, max_episodes=2)
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        s.store(MemoryRecord(id="r2", content="b", cycle=2))
        s.store(MemoryRecord(id="r3", content="c", cycle=4))
        assert len(s._episodes) == 2


# =========================================================================
# Semantic Pointer operations
# =========================================================================


class TestSemanticPointer:
    def test_random_vector_normalized(self):
        sp = SemanticPointer.random(64)
        assert sp.dimension == 64
        norm = math.sqrt(sum(x * x for x in sp.vector))
        assert abs(norm - 1.0) < 1e-6

    def test_cosine_similarity_self(self):
        sp = SemanticPointer.random(64)
        assert abs(sp.similarity(sp) - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        sp_a = SemanticPointer([1.0, 0.0], vocabulary=None)
        sp_b = SemanticPointer([0.0, 1.0], vocabulary=None)
        assert abs(sp_a.similarity(sp_b)) < 1e-6

    def test_bind_unbind_roundtrip(self):
        a = SemanticPointer.random(64)
        b = SemanticPointer.random(64)
        bound = a.bind(b)
        recovered = bound.unbind(b)
        sim = a.similarity(recovered)
        assert sim > 0.5

    def test_bind_inverse_roundtrip(self):
        a = SemanticPointer.random(64)
        b = SemanticPointer.random(64)
        bound = a.bind(b)
        recovered = bound.bind(b.inverse())
        sim = a.similarity(recovered)
        assert sim > 0.5

    def test_superposition_preserves_similarity(self):
        a = SemanticPointer.random(64)
        b = SemanticPointer.random(64)
        c = a + b
        assert a.similarity(c) > 0.5
        assert b.similarity(c) > 0.5

    def test_from_string_deterministic(self):
        a = SemanticPointer.from_string("hello", dim=64)
        b = SemanticPointer.from_string("hello", dim=64)
        assert abs(a.similarity(b) - 1.0) < 1e-6

    def test_from_string_distinct(self):
        a = SemanticPointer.from_string("hello", dim=64)
        b = SemanticPointer.from_string("world", dim=64)
        sim = a.similarity(b)
        assert sim < 0.5

    def test_encode_content(self):
        sp = encode_content("hello", dim=64)
        assert sp.dimension == 64

    def test_encode_content_dict(self):
        sp = encode_content({"foo": "bar"}, dim=64)
        assert sp.dimension == 64

    def test_encode_content_deterministic(self):
        a = encode_content({"x": 1}, dim=64)
        b = encode_content({"x": 1}, dim=64)
        assert abs(a.similarity(b) - 1.0) < 1e-6


# =========================================================================
# SPSCA Memory Strategy (real semantic pointers)
# =========================================================================


class TestSPSCAMemoryStrategy:
    def test_store_and_exact_retrieve(self):
        s = SPSCAMemoryStrategy(max_size=10, similarity_threshold=0.7)
        s.store(MemoryRecord(id="r1", content="hello world", cycle=0, importance=0.9))
        result = s.retrieve(MemoryQuery(query="hello world", min_importance=0.5))
        assert len(result.records) == 1
        assert result.records[0].id == "r1"

    def test_no_match_for_dissimilar_content(self):
        s = SPSCAMemoryStrategy(max_size=10, similarity_threshold=0.7)
        s.store(MemoryRecord(id="r1", content="obstacle at north", cycle=0, importance=0.9))
        result = s.retrieve(MemoryQuery(query="completely different", min_importance=0.5))
        assert len(result.records) == 0

    def test_retrieve_empty_query_returns_all(self):
        s = SPSCAMemoryStrategy(max_size=10, similarity_threshold=0.0)
        s.store(MemoryRecord(id="r1", content="a", cycle=0, importance=0.9))
        s.store(MemoryRecord(id="r2", content="b", cycle=0, importance=0.9))
        result = s.retrieve(MemoryQuery(query="", min_importance=0.0))
        assert len(result.records) == 2

    def test_forget_compresses_into_chunks(self):
        s = SPSCAMemoryStrategy(forget_threshold=0.3, max_size=100)
        s.store(MemoryRecord(id="r1", content="low", cycle=0, importance=0.1, record_type="obs"))
        s.store(MemoryRecord(id="r2", content="high", cycle=0, importance=0.9, record_type="obs"))
        forgotten = s.forget(current_cycle=0)
        assert forgotten == 1
        assert s.size == 1
        assert s.chunk_count == 1

    def test_clear(self):
        s = SPSCAMemoryStrategy()
        s.store(MemoryRecord(id="r1", content="a", cycle=0))
        s.clear()
        assert s.size == 0
        assert s.chunk_count == 0

    def test_enforce_limit_creates_chunks(self):
        s = SPSCAMemoryStrategy(max_size=5, max_individual=3)
        for i in range(5):
            s.store(MemoryRecord(
                id=f"r{i}", content=f"data_{i}", cycle=i,
                importance=0.1 + i * 0.2,
            ))
        assert s.size <= 5
        assert s.chunk_count > 0

    def test_metrics(self):
        s = SPSCAMemoryStrategy(max_size=10, similarity_threshold=0.0)
        s.store(MemoryRecord(id="r1", content="x", cycle=0, importance=0.9))
        s.retrieve(MemoryQuery(query=""))
        m = s.metrics
        assert m.strategy_name == "spsca"
        assert m.total_records == 1
        assert m.retrieval_count == 1

    def test_total_stored_includes_chunks(self):
        s = SPSCAMemoryStrategy(forget_threshold=0.3, max_size=100)
        s.store(MemoryRecord(id="r1", content="a", cycle=0, importance=0.1, record_type="obs"))
        s.forget(current_cycle=0)
        assert s.total_stored == s.size + s.chunk_count


# =========================================================================
# Memory cognitive node
# =========================================================================


class TestMemory:
    def test_execute_stores_pending(self):
        strategy = FIFOMemoryStrategy(max_size=10)
        mem = Memory(strategy=strategy)
        mem.store(MemoryRecord(id="r1", content="test", cycle=0))
        result = mem.execute(RobotState(), RuntimeContext())
        assert result.metrics["stored"] == 1
        assert strategy.size == 1

    def test_execute_forgets(self):
        strategy = PriorityMemoryStrategy(forget_below=0.3)
        mem = Memory(strategy=strategy)
        mem.store(MemoryRecord(id="r1", content="low", cycle=0, importance=0.1))
        mem.store(MemoryRecord(id="r2", content="high", cycle=0, importance=0.9))
        mem.execute(RobotState(), RuntimeContext())
        mem.execute(RobotState(), RuntimeContext())
        assert strategy.size == 1

    def test_ask(self):
        strategy = FIFOMemoryStrategy(max_size=10)
        mem = Memory(strategy=strategy)
        mem.store(MemoryRecord(id="r1", content="stored", cycle=0))
        mem.execute(RobotState(), RuntimeContext())
        result = mem.ask(MemoryQuery(limit=10))
        assert len(result.records) == 1

    def test_different_strategies_same_interface(self):
        strategies = [
            FIFOMemoryStrategy(max_size=10),
            TimeDecayMemoryStrategy(max_size=10),
            PriorityMemoryStrategy(max_size=10),
            EpisodicMemoryStrategy(max_episodes=10),
            SPSCAMemoryStrategy(max_size=10, similarity_threshold=0.0),
        ]
        for strategy in strategies:
            record = MemoryRecord(id="r1", content="test", cycle=0)
            strategy.store(record)
            result = strategy.retrieve(MemoryQuery(limit=10))
            assert len(result.records) == 1, f"Failed for {type(strategy).__name__}"
            assert result.records[0].id == "r1"
            m = strategy.metrics
            assert m.total_records == 1
            strategy.clear()
            assert strategy.size == 0


# =========================================================================
# Integration: Memory stores observations between StateEstimation and Planning
# =========================================================================


class TestMemoryIntegration:
    def test_memory_stores_observations_across_cycles(self):
        strategy = FIFOMemoryStrategy(max_size=100)
        mem = Memory(strategy=strategy)

        for cycle in range(5):
            record = MemoryRecord(
                id=f"obs_{cycle}",
                content={"obstacle_count": cycle, "cycle": cycle},
                cycle=cycle,
                importance=0.5 + cycle * 0.1,
                record_type="observation",
            )
            mem.store(record)
            mem.execute(RobotState(), RuntimeContext())

        assert strategy.size == 5
        result = mem.ask(MemoryQuery(record_types=["observation"], limit=10))
        assert len(result.records) == 5

    def test_memory_does_not_grow_unbounded(self):
        strategy = FIFOMemoryStrategy(max_size=10)
        mem = Memory(strategy=strategy)

        for cycle in range(100):
            record = MemoryRecord(
                id=f"obs_{cycle}",
                content={"cycle": cycle},
                cycle=cycle,
                importance=0.5,
            )
            mem.store(record)
            mem.execute(RobotState(), RuntimeContext())

        assert strategy.size == 10

    def test_ask_empty_memory(self):
        strategy = FIFOMemoryStrategy(max_size=10)
        mem = Memory(strategy=strategy)
        result = mem.ask(MemoryQuery(limit=10))
        assert len(result.records) == 0
