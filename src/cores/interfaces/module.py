from abc import ABC, abstractmethod
from typing import List, Any
from pydantic import BaseModel, Field
from cores.core import RobotState, RuntimeContext
from cores.events import Event


class ModuleResult(BaseModel):
    """
    ModuleResult represents the outcome of a module's execution.
    """
    module_name: str
    success: bool = True
    data: Any = None
    events: List[Event] = Field(default_factory=list)
    execution_time_ms: float = 0.0


class Module(ABC):
    """
    Abstract base class for all cognitive modules.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        """
        Perform computation based on the current state and context.
        """
        pass
