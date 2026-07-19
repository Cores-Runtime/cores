from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MissionState(BaseModel):
    mission_id: str = Field(default="")
    state: str = Field(default="idle")
    progress: float = Field(default=0.0, ge=0.0, le=1.0)


class ModuleState(BaseModel):
    name: str
    status: str = Field(default="active")
    priority: int = Field(default=0)
    safety_weight: float = Field(default=0.0)
    mission_weight: float = Field(default=0.0)
    urgency_weight: float = Field(default=0.0)
    compute_cost: float = Field(default=0.0)
    time_cost_ms: float = Field(default=0.0)
    energy_cost: float = Field(default=0.0)
    is_safety_critical: bool = Field(default=False)
    is_diagnostic: bool = Field(default=False)
    is_recovery: bool = Field(default=False)
    is_localization: bool = Field(default=False)


class SchedulerState(BaseModel):
    policy: str = Field(default="")
    mode: str = Field(default="default")
    cycle_count: int = Field(default=0)
    selected_modules: List[str] = Field(default_factory=list)
    deferred_modules: List[str] = Field(default_factory=list)
    resource_usage: Dict[str, float] = Field(default_factory=dict)
    constraints_active: List[str] = Field(default_factory=list)
    constraint_violation: bool = Field(default=False)
    decision_time_ms: float = Field(default=0.0)
    scores: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    lexicographic_value: Optional[Dict[str, float]] = None


class RobotSnapshot(BaseModel):
    battery_level: float = Field(default=1.0)
    position: Dict[str, float] = Field(default_factory=dict)
    velocity: Dict[str, float] = Field(default_factory=dict)
    flags: Dict[str, bool] = Field(default_factory=dict)


class EventsSnapshot(BaseModel):
    cycle_events: List[Dict[str, Any]] = Field(default_factory=list)
    obstacles: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    recoveries: List[Dict[str, Any]] = Field(default_factory=list)


class ExplainabilityState(BaseModel):
    module_changes: List[str] = Field(default_factory=list)
    scheduler_rationale: str = Field(default="")


class RuntimeState(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    mission: MissionState = Field(default_factory=MissionState)
    modules: List[ModuleState] = Field(default_factory=list)
    active_module_names: List[str] = Field(default_factory=list)
    sleeping_module_names: List[str] = Field(default_factory=list)
    suspended_module_names: List[str] = Field(default_factory=list)
    scheduler: SchedulerState = Field(default_factory=SchedulerState)
    robot: RobotSnapshot = Field(default_factory=RobotSnapshot)
    events: EventsSnapshot = Field(default_factory=EventsSnapshot)
    explainability: ExplainabilityState = Field(default_factory=ExplainabilityState)
