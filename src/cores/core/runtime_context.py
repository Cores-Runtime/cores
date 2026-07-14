from typing import Dict, Any
from pydantic import BaseModel, Field


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
