from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Dict, FrozenSet, List, Optional
from pydantic import BaseModel, Field
from cores.core import RobotState, RuntimeContext
from cores.events import Event


class ModuleStatus(StrEnum):
    """
    Represents the execution status of a module.
    """
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"


class ModuleResult(BaseModel):
    """
    ModuleResult represents the complete boundary output of a module's execution cycle.
    """
    module_name: str
    status: ModuleStatus = ModuleStatus.SUCCESS
    events: List[Event] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ModuleProfile:
    """
    Static scheduling metadata used by adaptive policies.
    """

    safety_weight: float = 0.0
    mission_weight: float = 0.0
    urgency_weight: float = 0.0
    compute_cost: float = 0.0
    time_cost_ms: float = 0.0
    energy_cost: float = 0.0
    mission_tags: FrozenSet[str] = field(default_factory=frozenset)
    is_safety_critical: bool = False
    is_diagnostic: bool = False
    is_recovery: bool = False
    is_localization: bool = False


class Module(ABC):
    """
    Abstract base class for all cognitive modules.
    """

    def __init__(
        self,
        name: str,
        priority: int = 0,
        profile: Optional[ModuleProfile] = None,
    ) -> None:
        self.name = name
        self.priority = priority
        self.profile = profile or ModuleProfile()

    @abstractmethod
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        """
        Perform computation based on the current state and context.
        """
        pass
