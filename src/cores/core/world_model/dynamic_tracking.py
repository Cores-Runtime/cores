from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from cores.core.world_model.types import (
    EnvironmentState,
    DetectedObject,
    UncertaintyState,
)
from cores.core.world_model.interface import WorldModelStrategy


class KalmanState:
    __slots__ = ("x", "y", "vx", "vy", "P", "confidence", "last_updated", "object_type", "properties")

    def __init__(
        self,
        object_id: str,
        object_type: str,
        x: float = 0.0,
        y: float = 0.0,
        vx: float = 0.0,
        vy: float = 0.0,
        confidence: float = 0.0,
        cycle: int = 0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.P: List[List[float]] = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 2.0, 0.0],
            [0.0, 0.0, 0.0, 2.0],
        ]
        self.confidence = confidence
        self.last_updated = cycle
        self.object_type = object_type
        self.properties = properties or {}


class DynamicTrackingWorldModel(WorldModelStrategy):
    """Physical reasoning strategy using a 4-DOF Kalman filter for velocity-aware tracking."""
    def __init__(
        self,
        dt: float = 1.0,
        process_noise: float = 0.1,
        measurement_noise: float = 0.5,
        velocity_decay: float = 0.95,
    ) -> None:
        self._dt = dt
        self._process_noise = process_noise
        self._measurement_noise = measurement_noise
        self._velocity_decay = velocity_decay
        self._tracks: Dict[str, KalmanState] = {}
        self._environment: EnvironmentState = EnvironmentState()
        self._uncertainty: UncertaintyState = UncertaintyState()
        self._last_update_cycle: int = 0

    # --- WorldModel interface ---

    @property
    def environment(self) -> EnvironmentState:
        return self._environment

    @property
    def objects(self) -> List[DetectedObject]:
        return [
            DetectedObject(
                id=tid,
                object_type=ts.object_type,
                position={"x": ts.x, "y": ts.y},
                confidence=ts.confidence,
                last_seen_cycle=ts.last_updated,
                properties={
                    **ts.properties,
                    "vx": ts.vx,
                    "vy": ts.vy,
                    "covariance_xx": ts.P[0][0],
                    "covariance_yy": ts.P[1][1],
                },
            )
            for tid, ts in self._tracks.items()
        ]

    @property
    def uncertainty(self) -> UncertaintyState:
        return self._uncertainty

    @property
    def obstacle_count(self) -> int:
        return sum(
            1 for t in self._tracks.values()
            if t.object_type == "obstacle" and t.confidence > 0.3
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
        x = position.get("x", 0.0)
        y = position.get("y", 0.0)
        measurement = [x, y]

        if object_id in self._tracks:
            ts = self._tracks[object_id]
            dt = max(0.001, cycle - ts.last_updated) * self._dt
            self._predict(ts, dt)
            self._update(ts, measurement, confidence, cycle)
            ts.object_type = object_type
            ts.confidence = min(1.0, ts.confidence + 0.05)
            ts.last_updated = cycle
            if properties:
                ts.properties.update(properties)
        else:
            ts = KalmanState(
                object_id=object_id,
                object_type=object_type,
                x=x,
                y=y,
                confidence=confidence,
                cycle=cycle,
                properties=properties or {},
            )
            self._tracks[object_id] = ts

        self._last_update_cycle = cycle

        return DetectedObject(
            id=object_id,
            object_type=object_type,
            position={"x": ts.x, "y": ts.y},
            confidence=ts.confidence,
            last_seen_cycle=cycle,
            properties=properties or {},
        )

    def get_object(self, object_id: str) -> Optional[DetectedObject]:
        ts = self._tracks.get(object_id)
        if ts is None:
            return None
        return DetectedObject(
            id=object_id,
            object_type=ts.object_type,
            position={"x": ts.x, "y": ts.y},
            confidence=ts.confidence,
            last_seen_cycle=ts.last_updated,
            properties={
                **ts.properties,
                "vx": ts.vx,
                "vy": ts.vy,
            },
        )

    def get_objects_by_type(self, object_type: str) -> List[DetectedObject]:
        return [
            self.get_object(tid)
            for tid, ts in self._tracks.items()
            if ts.object_type == object_type
        ]

    def remove_stale_objects(self, current_cycle: int, max_age: int = 10) -> int:
        before = len(self._tracks)
        stale_ids = [
            tid for tid, ts in self._tracks.items()
            if current_cycle - ts.last_updated > max_age
        ]
        for sid in stale_ids:
            del self._tracks[sid]
        return before - len(self._tracks)

    def remove_object(self, object_id: str) -> bool:
        if object_id not in self._tracks:
            return False
        del self._tracks[object_id]
        return True

    def predict(self, steps: int = 1, **kwargs: Any) -> Dict[str, Any]:
        predictions = {}
        for tid, ts in self._tracks.items():
            dt = steps * self._dt
            pred_x = ts.x + ts.vx * dt
            pred_y = ts.y + ts.vy * dt
            decayed_confidence = ts.confidence * (self._velocity_decay ** steps)
            predictions[tid] = {
                "position": {"x": pred_x, "y": pred_y},
                "velocity": {"vx": ts.vx, "vy": ts.vy},
                "confidence": max(0.0, decayed_confidence),
                "object_type": ts.object_type,
            }
        return {
            "predicted_objects": predictions,
            "method": "kalman_filter",
            "note": "DynamicTracking predicts using constant velocity Kalman filter",
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "type": "dynamic_tracking",
            "environment": self._environment.model_dump(),
            "tracks": [
                {
                    "id": tid,
                    "object_type": ts.object_type,
                    "x": ts.x,
                    "y": ts.y,
                    "vx": ts.vx,
                    "vy": ts.vy,
                    "covariance": ts.P,
                    "confidence": ts.confidence,
                    "last_updated": ts.last_updated,
                    "properties": dict(ts.properties),
                }
                for tid, ts in self._tracks.items()
            ],
            "uncertainty": self._uncertainty.model_dump(),
            "obstacle_count": self.obstacle_count,
            "last_update_cycle": self._last_update_cycle,
        }

    def explain(self) -> str:
        parts = [
            "DynamicTrackingWorldModel",
            f"{len(self._tracks)} tracked object(s) with Kalman filter",
        ]
        obstacles = self.obstacle_count
        if obstacles:
            parts.append(f"{obstacles} obstacle(s)")
        moving = sum(1 for t in self._tracks.values() if abs(t.vx) > 0.1 or abs(t.vy) > 0.1)
        if moving:
            parts.append(f"{moving} moving object(s)")
        if self.has_sensor_degradation:
            degraded = [k for k, v in self._uncertainty.sensor_health.items() if v < 0.5]
            parts.append(f"sensor degradation: {', '.join(degraded)}")
        return " | ".join(parts)

    # --- Kalman filter internals ---

    def _predict(self, state: KalmanState, dt: float) -> None:
        state.x += state.vx * dt
        state.y += state.vy * dt
        state.vx *= self._velocity_decay
        state.vy *= self._velocity_decay

        F = [
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        Q = [
            [self._process_noise, 0.0, 0.0, 0.0],
            [0.0, self._process_noise, 0.0, 0.0],
            [0.0, 0.0, self._process_noise * 0.5, 0.0],
            [0.0, 0.0, 0.0, self._process_noise * 0.5],
        ]
        new_P = self._mat_mul(F, self._mat_mul(state.P, self._mat_transpose(F)))
        new_P = self._mat_add(new_P, Q)
        state.P = new_P

    def _update(self, state: KalmanState, measurement: List[float], confidence: float, cycle: int) -> None:
        H = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ]
        R_scale = max(0.1, 1.0 - confidence + 0.1)
        R = [
            [self._measurement_noise * R_scale, 0.0],
            [0.0, self._measurement_noise * R_scale],
        ]
        y = [
            measurement[0] - H[0][0] * state.x - H[0][1] * state.y,
            measurement[1] - H[1][0] * state.x - H[1][1] * state.y,
        ]
        S = self._mat_mul(H, self._mat_mul(state.P, self._mat_transpose(H)))
        S = self._mat_add(S, R)
        try:
            S_inv = self._mat_inv_2x2(S)
        except ZeroDivisionError:
            return
        K = self._mat_mul(state.P, self._mat_mul(self._mat_transpose(H), S_inv))
        state.x += K[0][0] * y[0] + K[0][1] * y[1]
        state.y += K[1][0] * y[0] + K[1][1] * y[1]
        state.vx += K[2][0] * y[0] + K[2][1] * y[1]
        state.vy += K[3][0] * y[0] + K[3][1] * y[1]

        I_KH = self._mat_sub(
            [[1.0, 0.0, 0.0, 0.0],
             [0.0, 1.0, 0.0, 0.0],
             [0.0, 0.0, 1.0, 0.0],
             [0.0, 0.0, 0.0, 1.0]],
            self._mat_mul(K, H),
        )
        state.P = self._mat_mul(I_KH, state.P)

    # --- matrix helpers ---

    @staticmethod
    def _mat_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        rows_a, cols_a = len(A), len(A[0])
        rows_b, cols_b = len(B), len(B[0])
        result = [[0.0] * cols_b for _ in range(rows_a)]
        for i in range(rows_a):
            for j in range(cols_b):
                s = 0.0
                for k in range(cols_a):
                    s += A[i][k] * B[k][j]
                result[i][j] = s
        return result

    @staticmethod
    def _mat_transpose(A: List[List[float]]) -> List[List[float]]:
        return [[A[j][i] for j in range(len(A))] for i in range(len(A[0]))]

    @staticmethod
    def _mat_add(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]

    @staticmethod
    def _mat_sub(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]

    @staticmethod
    def _mat_inv_2x2(M: List[List[float]]) -> List[List[float]]:
        det = M[0][0] * M[1][1] - M[0][1] * M[1][0]
        if abs(det) < 1e-10:
            raise ZeroDivisionError("singular matrix")
        inv_det = 1.0 / det
        return [
            [M[1][1] * inv_det, -M[0][1] * inv_det],
            [-M[1][0] * inv_det, M[0][0] * inv_det],
        ]

    # --- query methods ---

    def get_track(self, object_id: str) -> Optional[KalmanState]:
        return self._tracks.get(object_id)

    def query_motion(self, object_id: str) -> Dict[str, float]:
        ts = self._tracks.get(object_id)
        if ts is None:
            return {}
        speed = math.sqrt(ts.vx ** 2 + ts.vy ** 2)
        return {
            "x": ts.x,
            "y": ts.y,
            "vx": ts.vx,
            "vy": ts.vy,
            "speed": speed,
        }

    def predict_position_at(self, object_id: str, future_steps: int = 1) -> Optional[Dict[str, float]]:
        ts = self._tracks.get(object_id)
        if ts is None:
            return None
        dt = future_steps * self._dt
        decay = self._velocity_decay ** future_steps
        return {
            "x": ts.x + ts.vx * dt * decay,
            "y": ts.y + ts.vy * dt * decay,
            "confidence": ts.confidence * decay,
        }
