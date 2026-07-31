"""Pure algorithm tests for SPSCA as a NarratorStrategy.

Migrated from the old SPSCAMemoryStrategy tests.
Tests verify the algorithm itself, not storage strategy behavior.
"""

from cores.core.memory.interface import MemoryRecord
from cores.core.logger import SPSCALogger
from cores.core.memory.semantic_pointers import (
    SemanticChunk,
    encode_content,
)


def make_outcome_record(rid: str, action: str, result: str = "Success", cycle: int = 0) -> MemoryRecord:
    return MemoryRecord(
        id=rid, content={"action": action, "result": result},
        cycle=cycle, importance=0.8,
    )


class TestSPSCACompression:
    def test_empty_records_returns_empty(self):
        narr = SPSCALogger()
        result = narr.compress([])
        assert result == []

    def test_single_record_compresses(self):
        narr = SPSCALogger()
        records = [make_outcome_record("r1", "OpenDoor")]
        result = narr.compress(records)
        assert len(result) == 1
        assert result[0].topic == "observation"

    def test_multiple_records_same_topic(self):
        narr = SPSCALogger()
        records = [
            make_outcome_record("r1", "OpenDoor", "Success", cycle=1),
            make_outcome_record("r2", "OpenDoor", "Failed", cycle=2),
        ]
        result = narr.compress(records)
        assert len(result) == 1

    def test_different_topics_separate_narratives(self):
        narr = SPSCALogger()
        from cores.core.memory import MemoryType
        records = [
            MemoryRecord(id="r1", content={"action": "OpenDoor"}, cycle=1, importance=0.8, record_type=MemoryType.OUTCOME),
            MemoryRecord(id="r2", content={"action": "Navigate"}, cycle=2, importance=0.8, record_type=MemoryType.ACTION),
        ]
        result = narr.compress(records)
        assert len(result) == 2


class TestSPSCAEncoding:
    def test_encode_content_deterministic(self):
        a = encode_content({"x": 1}, dim=64)
        b = encode_content({"x": 1}, dim=64)
        assert abs(a.similarity(b) - 1.0) < 1e-6

    def test_different_content_different_vectors(self):
        a = encode_content("hello", dim=64)
        b = encode_content("world", dim=64)
        assert a.similarity(b) < 0.9

    def test_semantic_pointer_binding(self):
        robot = encode_content("Robot", dim=128)
        action = encode_content("picked", dim=128)
        obj = encode_content("Medicine", dim=128)

        bound = robot.bind(action).bind(obj)
        recovered = bound.unbind(obj).unbind(action)
        sim = robot.similarity(recovered)
        assert sim > 0.5

    def test_semantic_chunk_merge(self):
        sp1 = encode_content("record_a", dim=64)
        sp2 = encode_content("record_b", dim=64)
        chunk = SemanticChunk("test", sp1)
        chunk.merge(sp2, 0.5)
        assert chunk.count == 2

    def test_compressed_narrative_has_confidence(self):
        narr = SPSCALogger()
        records = [make_outcome_record("r1", "OpenDoor") for _ in range(5)]
        result = narr.compress(records)
        assert len(result) == 1
        assert 0 <= result[0].confidence <= 1.0
