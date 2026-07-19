"""
Streaming Spatial Kinematic Physics Mapping (SSKPM)

SSKPM is the novel world-modeling algorithm proposed by CORES.
It integrates spatial indexing, kinematic state estimation, Bayesian
confidence fusion, semantic annotation, and streaming incremental
updates into a single unified representation.

Design decisions are documented inline.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from cores.core.world_model.types import (
    EnvironmentState,
    DetectedObject,
    UncertaintyState,
)
from cores.core.world_model.interface import WorldModelStrategy


class SpatialChunk:
    """
    A spatial region (tile) that contains object references.
    Uses fixed-size grid partitioning for O(1) region lookup.
    """
    __slots__ = ("gx", "gy", "object_ids")

    def __init__(self, gx: int, gy: int) -> None:
        self.gx = gx
        self.gy = gy
        self.object_ids: Set[str] = set()


class KinematicState:
    """
    Full physical state of a tracked entity.

    Position, velocity, and acceleration are tracked per-axis,
    along with a full 6x6 covariance matrix for uncertainty propagation.
    """
    __slots__ = (
        "x", "y", "z",
        "vx", "vy", "vz",
        "ax", "ay", "az",
        "covariance", "confidence",
        "first_seen", "last_seen",
        "object_type", "semantic_tags",
        "properties", "track_id",
    )

    def __init__(
        self,
        track_id: str,
        object_type: str,
        x: float = 0.0, y: float = 0.0, z: float = 0.0,
        cycle: int = 0,
        confidence: float = 0.0,
        semantic_tags: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.track_id = track_id
        self.object_type = object_type
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = 0.0, 0.0, 0.0
        self.ax, self.ay, self.az = 0.0, 0.0, 0.0
        n = 9
        self.covariance: List[List[float]] = [
            [1.0 if i == j else 0.0 for j in range(n)]
            for i in range(n)
        ]
        self.confidence = confidence
        self.first_seen = cycle
        self.last_seen = cycle
        self.semantic_tags = semantic_tags or []
        self.properties = properties or {}


class SSKPM(WorldModelStrategy):
    """
    CORES' proposed physical reasoning strategy combining spatial chunks,
    kinematic state estimation, Bayesian fusion, and semantic annotation.
    """
    """
    Streaming Spatial Kinematic Physics Mapper.

    Design rationale:
    - Uses a 2.5D spatial chunk index (grid-based) for efficient region queries.
    - Each tracked object maintains a kinematic state (pos, vel, accel)
      with a full covariance matrix for uncertainty.
    - Streaming updates: associate → fuse → predict → cleanup.
    - Confidence fuses observation confidence with temporal decay.
    - Semantic tags enable cross-modal reasoning.
    - Every update records metadata for explainability.
    """

    def __init__(
        self,
        chunk_size: float = 5.0,
        world_width: float = 500.0,
        world_height: float = 500.0,
        origin_x: float = -250.0,
        origin_y: float = -250.0,
        dt: float = 1.0,
        process_noise: float = 0.05,
        measurement_noise: float = 0.3,
        velocity_decay: float = 0.9,
        acceleration_decay: float = 0.8,
        confidence_decay: float = 0.05,
        association_distance: float = 3.0,
        max_track_age: int = 20,
    ) -> None:
        self._chunk_size = chunk_size
        self._world_width = world_width
        self._world_height = world_height
        self._origin_x = origin_x
        self._origin_y = origin_y
        self._dt = dt
        self._process_noise = process_noise
        self._measurement_noise = measurement_noise
        self._velocity_decay = velocity_decay
        self._acceleration_decay = acceleration_decay
        self._confidence_decay = confidence_decay
        self._association_distance = association_distance
        self._max_track_age = max_track_age

        nx = int(math.ceil(world_width / chunk_size))
        ny = int(math.ceil(world_height / chunk_size))
        self._num_chunks_x = max(1, nx)
        self._num_chunks_y = max(1, ny)

        self._chunks: List[List[Optional[SpatialChunk]]] = [
            [None for _ in range(self._num_chunks_y)]
            for _ in range(self._num_chunks_x)
        ]
        self._tracks: Dict[str, KinematicState] = {}
        self._environment: EnvironmentState = EnvironmentState()
        self._uncertainty: UncertaintyState = UncertaintyState()
        self._last_update_cycle: int = 0
        self._explain_log: List[str] = []

    # --- spatial chunk helpers ---

    def _world_to_chunk(self, x: float, y: float) -> Tuple[int, int]:
        gx = int((x - self._origin_x) / self._chunk_size)
        gy = int((y - self._origin_y) / self._chunk_size)
        return (
            max(0, min(gx, self._num_chunks_x - 1)),
            max(0, min(gy, self._num_chunks_y - 1)),
        )

    def _get_chunk(self, gx: int, gy: int, create: bool = False) -> Optional[SpatialChunk]:
        if 0 <= gx < self._num_chunks_x and 0 <= gy < self._num_chunks_y:
            chunk = self._chunks[gx][gy]
            if chunk is None and create:
                chunk = SpatialChunk(gx, gy)
                self._chunks[gx][gy] = chunk
            return chunk
        return None

    def _add_to_chunk(self, track_id: str, x: float, y: float) -> None:
        gx, gy = self._world_to_chunk(x, y)
        chunk = self._get_chunk(gx, gy, create=True)
        if chunk is not None:
            chunk.object_ids.add(track_id)

    def _remove_from_chunk(self, track_id: str, x: float, y: float) -> None:
        gx, gy = self._world_to_chunk(x, y)
        chunk = self._get_chunk(gx, gy)
        if chunk is not None:
            chunk.object_ids.discard(track_id)

    def _move_in_chunks(self, track_id: str, old_x: float, old_y: float, new_x: float, new_y: float) -> None:
        old_gx, old_gy = self._world_to_chunk(old_x, old_y)
        new_gx, new_gy = self._world_to_chunk(new_x, new_y)
        if old_gx != new_gx or old_gy != new_gy:
            old_chunk = self._get_chunk(old_gx, old_gy)
            if old_chunk is not None:
                old_chunk.object_ids.discard(track_id)
            new_chunk = self._get_chunk(new_gx, new_gy, create=True)
            if new_chunk is not None:
                new_chunk.object_ids.add(track_id)

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
                position={"x": ts.x, "y": ts.y, "z": ts.z},
                confidence=ts.confidence,
                last_seen_cycle=ts.last_seen,
                properties={
                    **ts.properties,
                    "vx": ts.vx,
                    "vy": ts.vy,
                    "vz": ts.vz,
                    "ax": ts.ax,
                    "ay": ts.ay,
                    "az": ts.az,
                    "semantic_tags": list(ts.semantic_tags),
                    "track_age": ts.last_seen - ts.first_seen,
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
            if t.object_type == "obstacle" and t.confidence > 0.2
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
        self._explain_log.append(
            f"env:{self._last_update_cycle}:updated({','.join(kwargs.keys())})"
        )

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
        z = position.get("z", 0.0)

        if object_id in self._tracks:
            ts = self._tracks[object_id]
            old_x, old_y = ts.x, ts.y
            dt = max(0.001, cycle - ts.last_seen) * self._dt
            self._predict_kinematic(ts, dt)

            effective_noise = self._measurement_noise * max(0.5, 1.0 - confidence)
            measurement = [x, y, z]
            self._update_kinematic(ts, measurement, effective_noise, dt)

            ts.object_type = object_type
            ts.confidence = min(1.0, ts.confidence + 0.1 * confidence)
            ts.last_seen = cycle
            if properties:
                ts.properties.update(properties)

            self._move_in_chunks(object_id, old_x, old_y, ts.x, ts.y)
            self._explain_log.append(
                f"update:{cycle}:{object_id}:pos=({x:.1f},{y:.1f}),conf={confidence:.2f}"
            )
        else:
            ts = KinematicState(
                track_id=object_id,
                object_type=object_type,
                x=x, y=y, z=z,
                cycle=cycle,
                confidence=confidence,
                semantic_tags=[object_type],
                properties=properties or {},
            )
            self._tracks[object_id] = ts
            self._add_to_chunk(object_id, x, y)
            self._explain_log.append(
                f"create:{cycle}:{object_id}:type={object_type},pos=({x:.1f},{y:.1f})"
            )

        self._last_update_cycle = cycle
        return DetectedObject(
            id=object_id,
            object_type=object_type,
            position={"x": ts.x, "y": ts.y, "z": ts.z},
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
            position={"x": ts.x, "y": ts.y, "z": ts.z},
            confidence=ts.confidence,
            last_seen_cycle=ts.last_seen,
            properties={
                **ts.properties,
                "vx": ts.vx, "vy": ts.vy, "vz": ts.vz,
                "ax": ts.ax, "ay": ts.ay, "az": ts.az,
                "semantic_tags": list(ts.semantic_tags),
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
            if current_cycle - ts.last_seen > max_age
        ]
        for sid in stale_ids:
            self.remove_object(sid)
        removed = before - len(self._tracks)
        if removed:
            self._explain_log.append(
                f"stale:{current_cycle}:removed={removed}"
            )
        return removed

    def remove_object(self, object_id: str) -> bool:
        ts = self._tracks.get(object_id)
        if ts is None:
            return False
        self._remove_from_chunk(object_id, ts.x, ts.y)
        del self._tracks[object_id]
        return True

    def predict(self, steps: int = 1, **kwargs: Any) -> Dict[str, Any]:
        predictions = {}
        for tid, ts in self._tracks.items():
            dt = steps * self._dt
            decay = self._velocity_decay ** steps
            pred_x = ts.x + ts.vx * dt * decay + 0.5 * ts.ax * dt * dt
            pred_y = ts.y + ts.vy * dt * decay + 0.5 * ts.ay * dt * dt
            pred_z = ts.z + ts.vz * dt * decay + 0.5 * ts.az * dt * dt
            pred_conf = max(0.0, ts.confidence - self._confidence_decay * steps)
            predictions[tid] = {
                "position": {"x": pred_x, "y": pred_y, "z": pred_z},
                "velocity": {"vx": ts.vx * decay, "vy": ts.vy * decay, "vz": ts.vz * decay},
                "confidence": pred_conf,
                "object_type": ts.object_type,
            }
        return {
            "predicted_objects": predictions,
            "method": "sskpm_kinematic",
            "steps": steps,
            "note": "SSKPM predicts using constant-acceleration kinematic model with velocity decay",
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "type": "sskpm",
            "version": "1.0",
            "chunk_size": self._chunk_size,
            "grid_dims": {"nx": self._num_chunks_x, "ny": self._num_chunks_y},
            "environment": self._environment.model_dump(),
            "tracks": [
                {
                    "id": tid,
                    "object_type": ts.object_type,
                    "position": {"x": ts.x, "y": ts.y, "z": ts.z},
                    "velocity": {"vx": ts.vx, "vy": ts.vy, "vz": ts.vz},
                    "acceleration": {"ax": ts.ax, "ay": ts.ay, "az": ts.az},
                    "confidence": ts.confidence,
                    "first_seen": ts.first_seen,
                    "last_seen": ts.last_seen,
                    "semantic_tags": list(ts.semantic_tags),
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
            "SSKPM v1.0",
            f"{len(self._tracks)} kinematic track(s)",
            f"grid: {self._num_chunks_x}x{self._num_chunks_y} chunks",
        ]
        obstacles = self.obstacle_count
        if obstacles:
            parts.append(f"{obstacles} obstacle(s)")
        moving = sum(
            1 for t in self._tracks.values()
            if abs(t.vx) > 0.1 or abs(t.vy) > 0.1
        )
        if moving:
            parts.append(f"{moving} moving")
        stale = sum(
            1 for t in self._tracks.values()
            if self._last_update_cycle - t.last_seen > 5
        )
        if stale:
            parts.append(f"{stale} aging")
        if self.has_sensor_degradation:
            degraded = [k for k, v in self._uncertainty.sensor_health.items() if v < 0.5]
            parts.append(f"sensor degradation: {', '.join(degraded)}")
        recent_ops = self._explain_log[-3:] if self._explain_log else []
        if recent_ops:
            parts.append(f"recent: {'; '.join(recent_ops)}")
        return " | ".join(parts)

    # --- kinematic model ---

    def _predict_kinematic(self, state: KinematicState, dt: float) -> None:
        half_dt2 = 0.5 * dt * dt

        state.x += state.vx * dt + state.ax * half_dt2
        state.y += state.vy * dt + state.ay * half_dt2
        state.z += state.vz * dt + state.az * half_dt2

        state.vx = state.vx * self._velocity_decay + state.ax * dt
        state.vy = state.vy * self._velocity_decay + state.ay * dt
        state.vz = state.vz * self._velocity_decay + state.az * dt

        state.ax *= self._acceleration_decay
        state.ay *= self._acceleration_decay
        state.az *= self._acceleration_decay

        n = 9
        F = self._make_jacobian(dt)
        new_P = self._mat_mul(F, self._mat_mul(state.covariance, self._mat_transpose(F)))
        Q = self._make_process_noise(dt)
        for i in range(n):
            for j in range(n):
                new_P[i][j] += Q[i][j]
        state.covariance = new_P

    def _update_kinematic(
        self, state: KinematicState, measurement: List[float],
        measurement_noise: float, dt: float,
    ) -> None:
        H = [
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ]
        R = [
            [measurement_noise, 0.0, 0.0],
            [0.0, measurement_noise, 0.0],
            [0.0, 0.0, measurement_noise],
        ]

        z = [
            measurement[0] - state.x,
            measurement[1] - state.y,
            measurement[2] - state.z,
        ]

        P_HT = self._mat_mul(state.covariance, self._mat_transpose(H))
        S = self._mat_mul(H, P_HT)
        for i in range(3):
            for j in range(3):
                S[i][j] += R[i][j]

        try:
            S_inv = self._mat_inv_3x3(S)
        except (ZeroDivisionError, ValueError):
            return

        K = self._mat_mul(P_HT, S_inv)

        state.x += K[0][0] * z[0] + K[0][1] * z[1] + K[0][2] * z[2]
        state.y += K[1][0] * z[0] + K[1][1] * z[1] + K[1][2] * z[2]
        state.z += K[2][0] * z[0] + K[2][1] * z[1] + K[2][2] * z[2]
        state.vx += K[3][0] * z[0] + K[3][1] * z[1] + K[3][2] * z[2]
        state.vy += K[4][0] * z[0] + K[4][1] * z[1] + K[4][2] * z[2]
        state.vz += K[5][0] * z[0] + K[5][1] * z[1] + K[5][2] * z[2]
        state.ax += K[6][0] * z[0] + K[6][1] * z[1] + K[6][2] * z[2]
        state.ay += K[7][0] * z[0] + K[7][1] * z[1] + K[7][2] * z[2]
        state.az += K[8][0] * z[0] + K[8][1] * z[1] + K[8][2] * z[2]

        I = [[1.0 if i == j else 0.0 for j in range(9)] for i in range(9)]
        KH = self._mat_mul(K, H)
        I_KH = [[I[i][j] - KH[i][j] for j in range(9)] for i in range(9)]
        state.covariance = self._mat_mul(I_KH, state.covariance)

    # --- matrix helpers ---

    def _make_jacobian(self, dt: float) -> List[List[float]]:
        decay = self._velocity_decay
        accel_decay = self._acceleration_decay
        return [
            [1.0, 0.0, 0.0, dt, 0.0, 0.0, 0.5*dt*dt, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, dt, 0.0, 0.0, 0.5*dt*dt, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0, dt, 0.0, 0.0, 0.5*dt*dt],
            [0.0, 0.0, 0.0, decay, 0.0, 0.0, dt, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, decay, 0.0, 0.0, dt, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, decay, 0.0, 0.0, dt],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, accel_decay, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, accel_decay, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, accel_decay],
        ]

    def _make_process_noise(self, dt: float) -> List[List[float]]:
        q = self._process_noise
        n = 9
        Q = [[0.0] * n for _ in range(n)]
        for i in range(n):
            Q[i][i] = q * (1.0 + 0.1 * i)
        return Q

    @staticmethod
    def _mat_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        rows_a, cols_a = len(A), len(A[0])
        cols_b = len(B[0])
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
    def _mat_inv_3x3(M: List[List[float]]) -> List[List[float]]:
        a, b, c = M[0][0], M[0][1], M[0][2]
        d, e, f = M[1][0], M[1][1], M[1][2]
        g, h, i = M[2][0], M[2][1], M[2][2]
        det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
        if abs(det) < 1e-12:
            raise ZeroDivisionError("singular matrix")
        inv_det = 1.0 / det
        return [
            [(e * i - f * h) * inv_det, (c * h - b * i) * inv_det, (b * f - c * e) * inv_det],
            [(f * g - d * i) * inv_det, (a * i - c * g) * inv_det, (c * d - a * f) * inv_det],
            [(d * h - e * g) * inv_det, (b * g - a * h) * inv_det, (a * e - b * d) * inv_det],
        ]

    # --- spatial queries ---

    def query_region(self, x_min: float, y_min: float, x_max: float, y_max: float) -> List[DetectedObject]:
        gx_min, gy_min = self._world_to_chunk(x_min, y_min)
        gx_max, gy_max = self._world_to_chunk(x_max, y_max)
        seen: Set[str] = set()
        result = []
        for gx in range(gx_min, gx_max + 1):
            for gy in range(gy_min, gy_max + 1):
                chunk = self._get_chunk(gx, gy)
                if chunk is not None:
                    for oid in chunk.object_ids:
                        if oid not in seen:
                            obj = self.get_object(oid)
                            if obj is not None:
                                result.append(obj)
                                seen.add(oid)
        return result

    def query_nearest(self, x: float, y: float, k: int = 5, object_type: Optional[str] = None) -> List[DetectedObject]:
        candidates = self.query_region(
            x - 50, y - 50, x + 50, y + 50
        )
        if object_type:
            candidates = [c for c in candidates if c.object_type == object_type]
        candidates.sort(
            key=lambda c: (c.position.get("x", 0) - x) ** 2 + (c.position.get("y", 0) - y) ** 2
        )
        return candidates[:k]

    def get_track(self, object_id: str) -> Optional[KinematicState]:
        return self._tracks.get(object_id)

    def clear_explain_log(self) -> None:
        self._explain_log.clear()
