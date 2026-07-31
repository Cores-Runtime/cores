"""SPSCA as a LoggerStrategy — compresses episodic records into narratives."""

from typing import Dict, List

from cores.core.memory.interface import MemoryRecord
from cores.core.memory.types import NarrativeRecord, MemoryType
from cores.core.memory.semantic_pointers import (
    SemanticPointer,
    SemanticChunk,
    encode_content,
    DEFAULT_DIM,
)
from cores.core.logger.interface import LoggerStrategy


class SPSCALogger(LoggerStrategy):
    """Semantic Pointer State Compression Algorithm — Narrator edition.

    Takes episodic records, encodes each as a semantic pointer,
    and compresses low-importance/episodic records into superposed
    narrative chunks.
    """

    def __init__(
        self,
        dim: int = DEFAULT_DIM,
        similarity_threshold: float = 0.6,
    ) -> None:
        self._dim = dim
        self._similarity_threshold = similarity_threshold

    def compress(self, records: List[MemoryRecord]) -> List[NarrativeRecord]:
        if not records:
            return []

        chunks: Dict[str, SemanticChunk] = {}
        narratives: List[NarrativeRecord] = []

        for record in records:
            sp = self._encode_record(record)
            key = record.record_type.value if hasattr(record.record_type, 'value') else str(record.record_type)

            if key not in chunks:
                chunks[key] = SemanticChunk(key, sp)
                chunks[key].importance = record.importance
                chunks[key].created_cycle = record.cycle
            else:
                chunks[key].merge(sp, record.importance)

        for chunk_key, chunk in chunks.items():
            narrative = NarrativeRecord(
                id=f"narr_{chunk_key}_{chunk.created_cycle}",
                content={"chunk_sp": str(chunk.sp), "source_count": chunk.count},
                cycle=chunk.created_cycle,
                confidence=min(1.0, chunk.count / 10.0),
                source_ids=[],
                topic=chunk_key,
                memory_type=MemoryType.NARRATIVE,
            )
            narratives.append(narrative)

        return narratives

    def _encode_record(self, record: MemoryRecord) -> SemanticPointer:
        return encode_content(record.content, dim=self._dim)
