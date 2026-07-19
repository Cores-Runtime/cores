from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from cores.core.world_model.types import (
    EnvironmentState,
    DetectedObject,
    UncertaintyState,
)
from cores.core.world_model.interface import WorldModelStrategy


class OccupancyGridCell:
    __slots__ = ("probability", "confidence", "last_seen", "object_type")

    def __init__(self) -> None:
        self.probability: float = 0.0
        self.confidence: float = 0.0
        self.last_seen: int = 0
        self.object_type: str = ""


class OccupancyGrid(WorldModelStrategy):
    """Physical reasoning strategy using log-odds occupancy grid with spatial indexing."""
    def __init__(
        self,
        width: int = 100,
        height: int = 100,
        resolution: float = 1.0,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        log_odds_occupied: float = 0.8,
        log_odds_free: float = -0.4,
        clamp_min: float = -4.0,
        clamp_max: float = 4.0,
    ) -> None:
        self._width = width
        self._height = height
        self._resolution = resolution
        self._origin_x = origin_x
        self._origin_y = origin_y
        self._log_odds_occupied = log_odds_occupied
        self._log_odds_free = log_odds_free
        self._clamp_min = clamp_min
        self._clamp_max = clamp_max
        self._grid: List[List[float]] = [
            [0.0 for _ in range(height)] for _ in range(width)
        ]
        self._objects: Dict[str, DetectedObject] = {}
        self._cell_objects: Dict[Tuple[int, int], List[str]] = {}
        self._environment: EnvironmentState = EnvironmentState()
        self._uncertainty: UncertaintyState = UncertaintyState()
        self._last_update_cycle: int = 0

    # --- coordinate helpers ---

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        gx = int((x - self._origin_x) / self._resolution)
        gy = int((y - self._origin_y) / self._resolution)
        return max(0, min(gx, self._width - 1)), max(0, min(gy, self._height - 1))

    def grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        return (
            gx * self._resolution + self._origin_x,
            gy * self._resolution + self._origin_y,
        )

    # --- WorldModel interface ---

    @property
    def environment(self) -> EnvironmentState:
        return self._environment

    @property
    def objects(self) -> List[DetectedObject]:
        return list(self._objects.values())

    @property
    def uncertainty(self) -> UncertaintyState:
        return self._uncertainty

    @property
    def obstacle_count(self) -> int:
        return sum(
            1 for o in self._objects.values() if o.object_type == "obstacle"
        )

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
        x, y = position.get("x", 0.0), position.get("y", 0.0)
        gx, gy = self.world_to_grid(x, y)
        self._update_cell(gx, gy, object_type, cycle, occupied=True)

        if object_id in self._objects:
            old = self._objects[object_id]
            old_x, old_y = old.position.get("x", 0.0), old.position.get("y", 0.0)
            old_gx, old_gy = self.world_to_grid(old_x, old_y)
            if (old_gx, old_gy) != (gx, gy):
                self._update_cell(old_gx, old_gy, "", 0, occupied=False)
                old_cell_key = (old_gx, old_gy)
                if old_cell_key in self._cell_objects:
                    self._cell_objects[old_cell_key] = [
                        oid for oid in self._cell_objects[old_cell_key] if oid != object_id
                    ]
            obj = old
            obj.object_type = object_type
            obj.position = position
            obj.confidence = confidence
            obj.last_seen_cycle = cycle
            if properties:
                obj.properties.update(properties)
        else:
            obj = DetectedObject(
                id=object_id,
                object_type=object_type,
                position=position,
                confidence=confidence,
                last_seen_cycle=cycle,
                properties=properties or {},
            )
            self._objects[object_id] = obj

        cell_key = (gx, gy)
        if cell_key not in self._cell_objects:
            self._cell_objects[cell_key] = []
        if object_id not in self._cell_objects[cell_key]:
            self._cell_objects[cell_key].append(object_id)

        self._last_update_cycle = cycle
        return obj

    def get_object(self, object_id: str) -> Optional[DetectedObject]:
        return self._objects.get(object_id)

    def get_objects_by_type(self, object_type: str) -> List[DetectedObject]:
        return [o for o in self._objects.values() if o.object_type == object_type]

    def remove_stale_objects(self, current_cycle: int, max_age: int = 10) -> int:
        before = len(self._objects)
        stale_ids = [
            oid for oid, o in self._objects.items()
            if current_cycle - o.last_seen_cycle > max_age
        ]
        for oid in stale_ids:
            self.remove_object(oid)
        return before - len(self._objects)

    def remove_object(self, object_id: str) -> bool:
        if object_id not in self._objects:
            return False
        obj = self._objects.pop(object_id)
        x, y = obj.position.get("x", 0.0), obj.position.get("y", 0.0)
        gx, gy = self.world_to_grid(x, y)
        cell_key = (gx, gy)
        if cell_key in self._cell_objects:
            self._cell_objects[cell_key] = [
                oid for oid in self._cell_objects[cell_key] if oid != object_id
            ]
        self._update_cell(gx, gy, "", 0, occupied=False)
        return True

    def predict(self, steps: int = 1, **kwargs: Any) -> Dict[str, Any]:
        return {
            "predicted_obstacle_count": self.obstacle_count,
            "method": "last_known",
            "note": "OccupancyGrid does not perform temporal prediction",
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "type": "occupancy_grid",
            "width": self._width,
            "height": self._height,
            "resolution": self._resolution,
            "origin": {"x": self._origin_x, "y": self._origin_y},
            "environment": self._environment.model_dump(),
            "objects": [o.model_dump() for o in self._objects.values()],
            "uncertainty": self._uncertainty.model_dump(),
            "obstacle_count": self.obstacle_count,
            "last_update_cycle": self._last_update_cycle,
            "cells": self._export_cells(),
        }

    def explain(self) -> str:
        parts = [
            f"OccupancyGrid ({self._width}x{self._height}, {self._resolution}m/cell)",
            f"terrain={self._environment.terrain}",
        ]
        occupied = self._count_occupied_cells()
        parts.append(f"{occupied} occupied cells, {self.obstacle_count} tracked obstacle(s)")
        if self.has_sensor_degradation:
            degraded = [k for k, v in self._uncertainty.sensor_health.items() if v < 0.5]
            parts.append(f"sensor degradation: {', '.join(degraded)}")
        return " | ".join(parts)

    # --- grid internals ---

    def _update_cell(self, gx: int, gy: int, object_type: str, cycle: int, occupied: bool) -> None:
        log_odds = self._log_odds_occupied if occupied else self._log_odds_free
        new_log_odds = self._grid[gx][gy] + log_odds
        self._grid[gx][gy] = max(self._clamp_min, min(self._clamp_max, new_log_odds))

    def get_cell_probability(self, gx: int, gy: int) -> float:
        log_odds = self._grid[gx][gy]
        return 1.0 - 1.0 / (1.0 + math.exp(log_odds))

    def query_occupancy(self, x: float, y: float) -> float:
        gx, gy = self.world_to_grid(x, y)
        return self.get_cell_probability(gx, gy)

    def get_objects_in_region(
        self, x_min: float, y_min: float, x_max: float, y_max: float
    ) -> List[DetectedObject]:
        gx_min, gy_min = self.world_to_grid(x_min, y_min)
        gx_max, gy_max = self.world_to_grid(x_max, y_max)
        result = []
        for gx in range(gx_min, gx_max + 1):
            for gy in range(gy_min, gy_max + 1):
                cell_key = (gx, gy)
                if cell_key in self._cell_objects:
                    for oid in self._cell_objects[cell_key]:
                        result.append(self._objects[oid])
        return result

    def _count_occupied_cells(self) -> int:
        threshold = 0.5
        return sum(
            1 for row in self._grid for val in row if 1.0 - 1.0 / (1.0 + math.exp(val)) > threshold
        )

    def _export_cells(self) -> List[Dict[str, Any]]:
        cells = []
        threshold = 0.5
        for gx in range(self._width):
            for gy in range(self._height):
                prob = 1.0 - 1.0 / (1.0 + math.exp(self._grid[gx][gy]))
                if prob > threshold:
                    wx, wy = self.grid_to_world(gx, gy)
                    cells.append({
                        "grid_x": gx,
                        "grid_y": gy,
                        "world_x": wx,
                        "world_y": wy,
                        "probability": round(prob, 3),
                        "object_ids": self._cell_objects.get((gx, gy), []),
                    })
        return cells
