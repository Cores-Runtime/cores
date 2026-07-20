from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from cores.core.planning.types import Goal


@dataclass
class Mission:
    mission_id: str
    goals: List[Goal]
    state: str = "active"
    priority: float = 1.0
    metadata: dict = field(default_factory=dict)
