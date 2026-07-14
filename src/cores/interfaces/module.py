from abc import ABC, abstractmethod
from enum import StrEnum
from typing import List, Any, Dict, Optional
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


class Module(ABC):
    """
    Abstract base class for all cognitive modules.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        """
        Perform computation based on the current state and context.
        """
        pass
