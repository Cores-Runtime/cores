"""Eliasmith-style Semantic Pointer operations in pure Python.

A Semantic Pointer is a high-dimensional vector (typically 512D) supporting:
  - **Binding** (circular convolution ⊗): combine two SPs into one
  - **Unbinding** (circular correlation ⋆): recover one SP from a bind
  - **Superposition** (+): compress multiple SPs into a single vector
  - **Similarity** (cosine): measure semantic relatedness

Usage:
    sp_a = SemanticPointer.random(512)
    sp_b = SemanticPointer.random(512)
    bound = sp_a.bind(sp_b)
    recovered = bound.unbind(sp_b)
    sim = sp_a.similarity(recovered)
"""

import math
import random
import hashlib
from typing import Dict, List, Optional, Union


# Default dimension matching typical SP literature
DEFAULT_DIM = 512


def _circular_convolution(a: List[float], b: List[float]) -> List[float]:
    """Circular convolution: (a ⊗ b)[k] = Σᵢ a[i] * b[(k - i) mod n]."""
    n = len(a)
    result = [0.0] * n
    for k in range(n):
        total = 0.0
        for i in range(n):
            j = (k - i) % n
            total += a[i] * b[j]
        result[k] = total
    return result


def _circular_correlation(a: List[float], b: List[float]) -> List[float]:
    """Circular correlation: (a ⋆ b)[k] = Σᵢ a[i] * b[(k + i) mod n].

    This is the unbinding operation. If c = a ⊗ b then c ⋆ b ≈ a.
    """
    n = len(a)
    result = [0.0] * n
    for k in range(n):
        total = 0.0
        for i in range(n):
            j = (k + i) % n
            total += a[i] * b[j]
        result[k] = total
    return result


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize(v: List[float]) -> List[float]:
    """Return L2-normalized copy."""
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0.0:
        return v[:]
    return [x / norm for x in v]


def _add_vectors(a: List[float], b: List[float]) -> List[float]:
    """Element-wise addition."""
    return [x + y for x, y in zip(a, b)]


def _scale(v: List[float], s: float) -> List[float]:
    """Scale vector by scalar."""
    return [x * s for x in v]


# ---------------------------------------------------------------------------
# Vocabulary: deterministic primitive vectors
# ---------------------------------------------------------------------------

class Vocabulary:
    """Deterministic vocabulary of primitive semantic pointers.

    Each symbol maps to a fixed random unit vector generated from a seeded RNG.
    This ensures reproducibility across runs.
    """

    def __init__(self, dim: int = DEFAULT_DIM, seed: int = 42) -> None:
        self._dim = dim
        self._rng = random.Random(seed)
        self._symbols: Dict[str, "SemanticPointer"] = {}

    def __getitem__(self, symbol: str) -> "SemanticPointer":
        if symbol not in self._symbols:
            vec = [self._rng.gauss(0, 1) for _ in range(self._dim)]
            vec = _normalize(vec)
            self._symbols[symbol] = SemanticPointer(vec, vocabulary=self)
        return self._symbols[symbol]

    def __contains__(self, symbol: str) -> bool:
        return symbol in self._symbols

    @property
    def dim(self) -> int:
        return self._dim


# Global default vocabulary
_default_vocab: Optional[Vocabulary] = None


def default_vocabulary(dim: int = DEFAULT_DIM) -> Vocabulary:
    global _default_vocab
    if _default_vocab is None or _default_vocab.dim != dim:
        _default_vocab = Vocabulary(dim=dim)
    return _default_vocab


# ---------------------------------------------------------------------------
# SemanticPointer
# ---------------------------------------------------------------------------

class SemanticPointer:
    """A high-dimensional vector with SP operations.

    Supports binding (⊗), unbinding (⋆), superposition (+),
    and cosine similarity.
    """

    def __init__(
        self,
        vector: Union[List[float], "SemanticPointer"],
        vocabulary: Optional[Vocabulary] = None,
    ) -> None:
        if isinstance(vector, SemanticPointer):
            self._v = vector._v[:]
            self._vocab = vector._vocab
        else:
            self._v = vector[:]
            self._vocab = vocabulary
        self._dim = len(self._v)

    @property
    def vector(self) -> List[float]:
        return self._v

    @property
    def dimension(self) -> int:
        return self._dim

    def copy(self) -> "SemanticPointer":
        return SemanticPointer(self._v[:], vocabulary=self._vocab)

    # --- Factory methods ---

    @classmethod
    def random(
        cls,
        dim: int = DEFAULT_DIM,
        rng: Optional[random.Random] = None,
    ) -> "SemanticPointer":
        if rng is None:
            rng = random.Random()
        vec = [rng.gauss(0, 1) for _ in range(dim)]
        return cls(_normalize(vec))

    @classmethod
    def zeros(cls, dim: int = DEFAULT_DIM) -> "SemanticPointer":
        return cls([0.0] * dim)

    @classmethod
    def from_string(
        cls,
        s: str,
        dim: int = DEFAULT_DIM,
        vocab: Optional[Vocabulary] = None,
    ) -> "SemanticPointer":
        """Deterministic SP from a string via seeded hash."""
        digest = hashlib.sha256(s.encode()).hexdigest()
        rng = random.Random(digest)
        vec = [rng.gauss(0, 1) for _ in range(dim)]
        return cls(_normalize(vec), vocabulary=vocab)

    # --- Core operations ---

    def bind(self, other: "SemanticPointer") -> "SemanticPointer":
        """Circular convolution: self ⊗ other.

        Combines two SPs into one. Used for role-filler binding.
        """
        return SemanticPointer(
            _circular_convolution(self._v, other._v),
            vocabulary=self._vocab or other._vocab,
        )

    def unbind(self, other: "SemanticPointer") -> "SemanticPointer":
        """Unbinding via convolution with inverse: self ⊗ other⁻¹.

        If c = a ⊗ b then c.unbind(b) ≈ a.
        This is the standard Eliasmith unbinding operation.
        """
        return self.bind(other.inverse())

    def inverse(self) -> "SemanticPointer":
        """Inverse for convolution: inv(self)[k] = self[(-k) mod n].

        So self.bind(other).unbind(self) ≈ other.
        """
        n = len(self._v)
        inv = [self._v[0]] + [self._v[n - i] for i in range(1, n)]
        return SemanticPointer(inv, vocabulary=self._vocab)

    def similarity(self, other: "SemanticPointer") -> float:
        """Cosine similarity between self and other."""
        return _cosine_similarity(self._v, other._v)

    def normalize(self) -> "SemanticPointer":
        """Return L2-normalized copy."""
        return SemanticPointer(_normalize(self._v), vocabulary=self._vocab)

    # --- Arithmetic ---

    def __add__(self, other: "SemanticPointer") -> "SemanticPointer":
        """Superposition: element-wise addition, then normalized."""
        raw = _add_vectors(self._v, other._v)
        return SemanticPointer(_normalize(raw), vocabulary=self._vocab or other._vocab)

    def __mul__(self, scalar: float) -> "SemanticPointer":
        return SemanticPointer(_scale(self._v, scalar), vocabulary=self._vocab)

    def __rmul__(self, scalar: float) -> "SemanticPointer":
        return self.__mul__(scalar)

    def __neg__(self) -> "SemanticPointer":
        return SemanticPointer([-x for x in self._v], vocabulary=self._vocab)

    def __sub__(self, other: "SemanticPointer") -> "SemanticPointer":
        return self + (-other)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticPointer):
            return NotImplemented
        return self._v == other._v

    def __repr__(self) -> str:
        return f"SemanticPointer(dim={self._dim})"


# ---------------------------------------------------------------------------
# Encoding helpers: map Python values to SemanticPointers
# ---------------------------------------------------------------------------

def encode_content(
    content: object,
    dim: int = DEFAULT_DIM,
) -> SemanticPointer:
    """Encode arbitrary Python content as a semantic pointer.

    Uses a deterministic hash of the JSON representation. This avoids
    expensive circular convolution during storage while preserving the
    property that identical content maps to identical vectors.

    For advanced structured queries, use bind()/unbind() manually on
    the returned SemanticPointer.
    """
    import json
    raw = json.dumps(content, sort_keys=True, default=str)
    return SemanticPointer.from_string(raw, dim=dim)


# ---------------------------------------------------------------------------
# Chunking: compress multiple SPs via superposition
# ---------------------------------------------------------------------------

class SemanticChunk:
    """A compressed chunk formed by superposing multiple semantic pointers.

    A chunk preserves approximate semantic content but loses individual
    record identity. It acts as a noisy summary of its constituents.
    """

    def __init__(self, chunk_id: str, sp: SemanticPointer) -> None:
        self.id = chunk_id
        self.sp = sp
        self.importance: float = 0.0
        self.count: int = 1
        self.created_cycle: int = 0

    def merge(self, other_sp: SemanticPointer, importance: float) -> None:
        """Merge another SP into this chunk via superposition."""
        self.sp = self.sp + other_sp
        self.count += 1
        self.importance = max(self.importance, importance)
