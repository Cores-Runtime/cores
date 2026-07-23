"""SPSCA memory using real Eliasmith-style semantic pointers.

Stores records as high-dimensional vectors (512D) supporting:
  - **Binding** (circular convolution) for role-filler encoding
  - **Superposition** for chunking/compression
  - **Cosine similarity** for retrieval

When `max_individual` records are exceeded, low-importance records are
compressed into chunks (superposed SPs) rather than dropped entirely.
"""

from typing import Any, Dict, List, Tuple

from cores.core.memory.interface import (
    MemoryRecord,
    MemoryQuery,
    MemoryResult,
    MemoryMetrics,
    MemoryStrategy,
)
from cores.core.memory.semantic_pointers import (
    DEFAULT_DIM,
    SemanticPointer,
    SemanticChunk,
    encode_content,
)


class SPSCAMemoryStrategy(MemoryStrategy):
    """Semantic Pointer State Compression Algorithm memory.

    Every stored record is encoded as a high-dimensional semantic pointer
    vector using role-filler binding. Retrieval uses real cosine similarity.

    Compression: when individual records exceed `max_individual`, low-
    importance records are merged into superposed *chunks*. Chunks preserve
    approximate semantic information for similarity queries but cannot be
    separated back into individual records.
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_individual: int = 500,
        similarity_threshold: float = 0.6,
        forget_threshold: float = 0.05,
        dim: int = DEFAULT_DIM,
    ) -> None:
        self._max_size = max_size
        self._max_individual = max_individual
        self._similarity_threshold = similarity_threshold
        self._forget_threshold = forget_threshold
        self._dim = dim

        self._records: Dict[str, MemoryRecord] = {}
        self._sp_map: Dict[str, SemanticPointer] = {}
        self._chunks: List[SemanticChunk] = []

        self._retrieval_count = 0
        self._insertion_count = 0
        self._forgetting_count = 0

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def _encode_content_sp(self, content: Any) -> SemanticPointer:
        """Encode record content as a semantic pointer for similarity matching."""
        return encode_content(content, dim=self._dim)

    def _encode_query(self, query: MemoryQuery) -> SemanticPointer:
        """Encode a query as a semantic pointer for similarity matching."""
        if not query.query.strip():
            return SemanticPointer.zeros(self._dim)
        return encode_content(query.query, dim=self._dim)

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def store(self, record: MemoryRecord) -> None:
        content_sp = self._encode_content_sp(record.content)
        self._records[record.id] = record
        self._sp_map[record.id] = content_sp
        self._insertion_count += 1
        self._enforce_limit()

    def store_batch(self, records: List[MemoryRecord]) -> None:
        for record in records:
            self.store(record)

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(self, query: MemoryQuery) -> MemoryResult:
        self._retrieval_count += 1
        query_sp = self._encode_query(query)
        has_query = bool(query.query.strip())

        scored: List[Tuple[float, MemoryRecord]] = []

        for rid, record in self._records.items():
            if not self._matches(record, query):
                continue
            sp = self._sp_map.get(rid)
            if sp is None:
                continue
            if has_query:
                sim = query_sp.similarity(sp)
                if sim < self._similarity_threshold:
                    continue
            else:
                sim = 0.5
            scored.append((sim, record))

        scored.sort(key=lambda x: x[0], reverse=True)
        records = [r for _, r in scored[: query.limit]]
        return MemoryResult(records=records, query=query)

    # ------------------------------------------------------------------
    # Forget
    # ------------------------------------------------------------------

    def forget(self, current_cycle: int) -> int:
        before = self.size
        to_chunk: List[str] = []

        for rid, record in self._records.items():
            if record.importance < self._forget_threshold:
                to_chunk.append(rid)

        for rid in to_chunk:
            record = self._records[rid]
            sp = self._sp_map.get(rid)
            if sp is not None:
                self._compress_into_chunk(record, sp)
            del self._records[rid]
            self._sp_map.pop(rid, None)

        removed = before - self.size
        self._forgetting_count += removed
        return removed

    def clear(self) -> None:
        self._records.clear()
        self._sp_map.clear()
        self._chunks.clear()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def total_stored(self) -> int:
        return self.size + self.chunk_count

    @property
    def metrics(self) -> MemoryMetrics:
        return MemoryMetrics(
            total_records=self.size,
            retrieval_count=self._retrieval_count,
            insertion_count=self._insertion_count,
            forgetting_count=self._forgetting_count,
            strategy_name="spsca",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _enforce_limit(self) -> None:
        """Enforce storage limits.

        If individual records exceed max_individual, compress the lowest-
        importance records into chunks.
        """
        while self.size > self._max_size:
            lowest_id = min(
                self._records.keys(),
                key=lambda rid: self._records[rid].importance,
            )
            record = self._records[lowest_id]
            sp = self._sp_map.get(lowest_id)
            if sp is not None:
                self._compress_into_chunk(record, sp)
            del self._records[lowest_id]
            self._sp_map.pop(lowest_id, None)

        while self.size > self._max_individual:
            lowest_id = min(
                self._records.keys(),
                key=lambda rid: self._records[rid].importance,
            )
            record = self._records[lowest_id]
            sp = self._sp_map.get(lowest_id)
            if sp is not None:
                self._compress_into_chunk(record, sp)
            del self._records[lowest_id]
            self._sp_map.pop(lowest_id, None)

    def _compress_into_chunk(
        self, record: MemoryRecord, sp: SemanticPointer
    ) -> None:
        """Merge a record's SP into a chunk.

        If a chunk with the same record_type exists, merge into it.
        Otherwise create a new chunk.
        """
        for chunk in self._chunks:
            if chunk.id == record.record_type:
                chunk.merge(sp, record.importance)
                return

        chunk = SemanticChunk(record.record_type, sp)
        chunk.importance = record.importance
        chunk.created_cycle = record.cycle
        self._chunks.append(chunk)

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
