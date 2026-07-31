"""SPSCA as a LoggerStrategy — compresses episodic records into narratives."""

from typing import Dict, List

from cores.core.memory.interface import MemoryRecord
from cores.core.memory.types import CompressionMetadata, NarrativeRecord, MemoryType
from cores.core.memory.semantic_pointers import (
    SemanticPointer,
    SemanticChunk,
    encode_content,
    DEFAULT_DIM,
)
from cores.core.logger.interface import LoggerStrategy


class SPSCALogger(LoggerStrategy):
    """Semantic Pointer State Compression Algorithm — Logger edition.

    Takes episodic records, encodes each as a semantic pointer,
    and compresses low-importance/episodic records into superposed
    narrative chunks. Each narrative carries provenance metadata
    (source ids, importance statistics) for explainability and replay.
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
        chunk_ids: Dict[str, List[str]] = {}
        chunk_importance: Dict[str, float] = {}

        for record in records:
            sp = self._encode_record(record)
            key = record.record_type.value if hasattr(record.record_type, 'value') else str(record.record_type)

            if key not in chunks:
                chunks[key] = SemanticChunk(key, sp)
                chunks[key].importance = record.importance
                chunks[key].created_cycle = record.cycle
                chunk_ids[key] = []
                chunk_importance[key] = 0.0
            else:
                chunks[key].merge(sp, record.importance)

            chunk_ids[key].append(record.id)
            chunk_importance[key] += record.importance

        narratives: List[NarrativeRecord] = []
        for chunk_key, chunk in chunks.items():
            source_ids = chunk_ids[chunk_key]
            total_importance = chunk_importance[chunk_key]
            source_count = len(source_ids)
            confidence = min(1.0, source_count / 10.0)
            metadata = CompressionMetadata(
                source_ids=list(source_ids),
                method="spsca",
                created_cycle=chunk.created_cycle,
                confidence=confidence,
                source_count=source_count,
                total_importance=round(total_importance, 4),
                mean_importance=round(total_importance / source_count, 4) if source_count else 0.0,
            )
            narrative = NarrativeRecord(
                id=f"narr_{chunk_key}_{chunk.created_cycle}",
                content={"chunk_sp": str(chunk.sp), "source_count": chunk.count},
                cycle=chunk.created_cycle,
                confidence=confidence,
                source_ids=list(source_ids),
                topic=chunk_key,
                memory_type=MemoryType.NARRATIVE,
                compression=metadata,
            )
            narratives.append(narrative)

        return narratives

    def _encode_record(self, record: MemoryRecord) -> SemanticPointer:
        return encode_content(record.content, dim=self._dim)
