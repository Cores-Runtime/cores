from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, FrozenSet, List, Optional, Set, TYPE_CHECKING

from pydantic import BaseModel, Field
from cores.events import Event

if TYPE_CHECKING:
    from cores.core.robot_state import RobotState
    from cores.core.runtime_context import RuntimeContext


class ModuleStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"


class ModuleResult(BaseModel):
    module_name: str
    status: ModuleStatus = ModuleStatus.SUCCESS
    events: List[Event] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None


class ModuleLifecycleStage(StrEnum):
    CREATED = "created"
    REGISTERED = "registered"
    STARTED = "started"
    STOPPED = "stopped"


@dataclass(frozen=True)
class ModuleProfile:
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
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    tags: FrozenSet[str] = field(default_factory=frozenset)
    dependencies: FrozenSet[str] = field(default_factory=frozenset)


class Module(ABC):
    def __init__(
        self,
        name: str,
        priority: int = 0,
        profile: Optional[ModuleProfile] = None,
    ) -> None:
        self.name = name
        self.priority = priority
        self.profile = profile or ModuleProfile()
        self._lifecycle_stage: ModuleLifecycleStage = ModuleLifecycleStage.CREATED

    @abstractmethod
    def execute(self, state: "RobotState", context: "RuntimeContext") -> ModuleResult:
        pass

    @property
    def lifecycle_stage(self) -> ModuleLifecycleStage:
        return self._lifecycle_stage

    def on_register(self, runtime: Any) -> None:
        self._lifecycle_stage = ModuleLifecycleStage.REGISTERED

    def on_startup(self) -> None:
        self._lifecycle_stage = ModuleLifecycleStage.STARTED

    def on_shutdown(self) -> None:
        self._lifecycle_stage = ModuleLifecycleStage.STOPPED

    @property
    def dependencies(self) -> FrozenSet[str]:
        return self.profile.dependencies

    @property
    def description(self) -> str:
        return self.profile.description

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()
