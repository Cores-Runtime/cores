from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from cores.core.world_model.types import (
    EnvironmentState,
    DetectedObject,
    UncertaintyState,
)


class WorldModelStrategy(ABC):
    @abstractmethod
    def update_environment(self, **kwargs: Any) -> None:
        ...

    @abstractmethod
    def upsert_object(
        self,
        object_id: str,
        object_type: str,
        position: Dict[str, float],
        confidence: float,
        cycle: int,
        properties: Optional[Dict[str, Any]] = None,
    ) -> DetectedObject:
        ...

    @abstractmethod
    def get_object(self, object_id: str) -> Optional[DetectedObject]:
        ...

    @abstractmethod
    def get_objects_by_type(self, object_type: str) -> List[DetectedObject]:
        ...

    @abstractmethod
    def remove_stale_objects(self, current_cycle: int, max_age: int = 10) -> int:
        ...

    @abstractmethod
    def remove_object(self, object_id: str) -> bool:
        ...

    @abstractmethod
    def predict(self, steps: int = 1, **kwargs: Any) -> Dict[str, Any]:
        ...

    @abstractmethod
    def serialize(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def explain(self) -> str:
        ...

    @property
    @abstractmethod
    def environment(self) -> EnvironmentState:
        ...

    @property
    @abstractmethod
    def objects(self) -> List[DetectedObject]:
        ...

    @property
    @abstractmethod
    def uncertainty(self) -> UncertaintyState:
        ...

    @property
    @abstractmethod
    def obstacle_count(self) -> int:
        ...

    @property
    @abstractmethod
    def has_sensor_degradation(self) -> bool:
        ...

    @property
    @abstractmethod
    def last_update_cycle(self) -> int:
        ...


WorldModel = WorldModelStrategy
