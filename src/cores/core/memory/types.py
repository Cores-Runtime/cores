from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class MemoryType(str, Enum):
    OBSERVATION = "observation"
    ACTION = "action"
    PLAN = "plan"
    OUTCOME = "outcome"
    EPISODE = "episode"
    SEMANTIC = "semantic"
    NARRATIVE = "narrative"


class RecordLifecycle(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    ARCHIVED = "archived"
    CONSOLIDATED = "consolidated"
    DISCARDED = "discarded"


@dataclass
class MemoryQuery:
    """Structured query for retrieving records from Memory.

    Planning never chooses episodic or semantic — Memory merges both.
    """

    memory_types: Optional[List[MemoryType]] = None
    location: Optional[str] = None
    action: Optional[str] = None
    topic: Optional[str] = None
    lifecycle: Optional[List[RecordLifecycle]] = None
    query_text: str = ""
    min_importance: float = 0.0
    max_age_cycles: Optional[int] = None
    max_results: int = 10


@dataclass
class NarrativeRecord:
    """A compressed narrative produced by the Narrator and stored in SemanticStore."""

    id: str
    content: Any
    cycle: int
    confidence: float = 0.5
    source_ids: List[str] = field(default_factory=list)
    topic: str = ""
    memory_type: MemoryType = MemoryType.NARRATIVE
