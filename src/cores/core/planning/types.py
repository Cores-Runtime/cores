from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Goal:
    goal_id: str
    description: str
    priority: float = 1.0
    category: str = "generic"
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    action_id: str
    name: str
    cost: float = 1.0
    duration_cycles: int = 1
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanCandidate:
    plan_id: str
    goal_id: str
    actions: List[Action]
    confidence: float = 1.0
    estimated_cost: float = 0.0
    estimated_duration_cycles: int = 0
    utility: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanningMetrics:
    planning_latency_ms: float = 0.0
    candidates_generated: int = 0
    goals_considered: int = 0
    replanning_triggered: bool = False
    strategy_name: str = ""


@dataclass(frozen=True)
class PlanningResult:
    candidates: List[PlanCandidate]
    selected: Optional[PlanCandidate] = None
    metrics: PlanningMetrics = field(default_factory=PlanningMetrics)
    context: Dict[str, Any] = field(default_factory=dict)
