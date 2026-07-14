from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RobotState(BaseModel):
    """
    RobotState is the single source of truth for the robot's observable state.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    battery_level: float = Field(default=1.0, ge=0.0, le=1.0)
    pose: Dict[str, float] = Field(default_factory=dict)  # e.g., {"x": 0.0, "y": 0.0, "theta": 0.0}
    velocity: Dict[str, float] = Field(default_factory=dict)
    mission_status: str = Field(default="idle")
    sensor_summaries: Dict[str, Any] = Field(default_factory=dict)
    flags: Dict[str, bool] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeContext(BaseModel):
    """
    RuntimeContext represents information about the runtime itself.
    """
    cycle_count: int = Field(default=0, ge=0)
    compute_budget: float = Field(default=1.0)  # Normalized 0.0 to 1.0
    time_budget_ms: float = Field(default=100.0)
    scheduler_mode: str = Field(default="default")
    is_emergency: bool = Field(default=False)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    profiling: Dict[str, Any] = Field(default_factory=dict)
