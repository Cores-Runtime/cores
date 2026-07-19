from typing import Any, Dict, List, Optional

from cores.core.world_model.types import (
    EnvironmentState,
    DetectedObject,
    UncertaintyState,
)
from cores.core.world_model.interface import WorldModelStrategy


class SimpleObjectRegistry(WorldModelStrategy):
    """Baseline physical reasoning strategy — flat object store with no spatial/kinematic reasoning."""
    def __init__(self) -> None:
        self._environment: EnvironmentState = EnvironmentState()
        self._objects: List[DetectedObject] = []
        self._uncertainty: UncertaintyState = UncertaintyState()
        self._last_update_cycle: int = 0

    @property
    def environment(self) -> EnvironmentState:
        return self._environment

    @property
    def objects(self) -> List[DetectedObject]:
        return self._objects

    @property
    def uncertainty(self) -> UncertaintyState:
        return self._uncertainty

    @property
    def obstacle_count(self) -> int:
        return len([o for o in self._objects if o.object_type == "obstacle"])

    @property
    def has_sensor_degradation(self) -> bool:
        return any(h < 0.5 for h in self._uncertainty.sensor_health.values())

    @property
    def last_update_cycle(self) -> int:
        return self._last_update_cycle

    def update_environment(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self._environment, key):
                setattr(self._environment, key, value)
        self._last_update_cycle = max(self._last_update_cycle, 0) + 1

    def upsert_object(
        self,
        object_id: str,
        object_type: str,
        position: Dict[str, float],
        confidence: float,
        cycle: int,
        properties: Optional[Dict[str, Any]] = None,
    ) -> DetectedObject:
        existing = next((o for o in self._objects if o.id == object_id), None)
        if existing:
            existing.object_type = object_type
            existing.position = position
            existing.confidence = confidence
            existing.last_seen_cycle = cycle
            if properties:
                existing.properties.update(properties)
            self._last_update_cycle = cycle
            return existing
        obj = DetectedObject(
            id=object_id,
            object_type=object_type,
            position=position,
            confidence=confidence,
            last_seen_cycle=cycle,
            properties=properties or {},
        )
        self._objects.append(obj)
        self._last_update_cycle = cycle
        return obj

    def get_object(self, object_id: str) -> Optional[DetectedObject]:
        return next((o for o in self._objects if o.id == object_id), None)

    def get_objects_by_type(self, object_type: str) -> List[DetectedObject]:
        return [o for o in self._objects if o.object_type == object_type]

    def remove_stale_objects(self, current_cycle: int, max_age: int = 10) -> int:
        before = len(self._objects)
        self._objects = [
            o for o in self._objects
            if current_cycle - o.last_seen_cycle <= max_age
        ]
        return before - len(self._objects)

    def remove_object(self, object_id: str) -> bool:
        before = len(self._objects)
        self._objects = [o for o in self._objects if o.id != object_id]
        return len(self._objects) < before

    def predict(self, steps: int = 1, **kwargs: Any) -> Dict[str, Any]:
        return {
            "predicted_obstacle_count": self.obstacle_count,
            "method": "none",
            "note": "SimpleObjectRegistry does not support prediction",
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "type": "simple_registry",
            "environment": self._environment.model_dump(),
            "objects": [o.model_dump() for o in self._objects],
            "uncertainty": self._uncertainty.model_dump(),
            "obstacle_count": self.obstacle_count,
            "last_update_cycle": self._last_update_cycle,
        }

    def explain(self) -> str:
        parts = [
            f"SimpleObjectRegistry with {len(self._objects)} objects",
            f"terrain={self._environment.terrain}",
            f"weather={self._environment.weather}",
        ]
        obstacles = self.obstacle_count
        if obstacles:
            parts.append(f"{obstacles} obstacle(s) tracked")
        if self.has_sensor_degradation:
            degraded = [
                k for k, v in self._uncertainty.sensor_health.items() if v < 0.5
            ]
            parts.append(f"sensor degradation: {', '.join(degraded)}")
        return " | ".join(parts)
