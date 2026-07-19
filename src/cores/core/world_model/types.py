from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EnvironmentState(BaseModel):
    terrain: str = Field(default="unknown")
    weather: str = Field(default="clear")
    temperature: float = Field(default=20.0)
    lighting: str = Field(default="day")
    hazards: List[Dict[str, Any]] = Field(default_factory=list)
    obstacle_distance: float = Field(default=10.0)


class DetectedObject(BaseModel):
    id: str
    object_type: str
    position: Dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(default=0.0)
    last_seen_cycle: int = Field(default=0)
    properties: Dict[str, Any] = Field(default_factory=dict)


class UncertaintyState(BaseModel):
    localization: float = Field(default=0.0, ge=0.0, le=1.0)
    mapping: float = Field(default=0.0, ge=0.0, le=1.0)
    perception: float = Field(default=0.0, ge=0.0, le=1.0)
    sensor_health: Dict[str, float] = Field(default_factory=dict)
