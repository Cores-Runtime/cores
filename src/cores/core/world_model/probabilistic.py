from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from cores.core.world_model.types import (
    EnvironmentState,
    DetectedObject,
    UncertaintyState,
)
from cores.core.world_model.interface import WorldModelStrategy


class BeliefState:
    __slots__ = ("mean", "variance", "confidence", "last_updated", "prior_weight")

    def __init__(
        self,
        mean: float = 0.0,
        variance: float = 1.0,
        confidence: float = 0.0,
        last_updated: int = 0,
        prior_weight: float = 1.0,
    ) -> None:
        self.mean = mean
        self.variance = variance
        self.confidence = confidence
        self.last_updated = last_updated
        self.prior_weight = prior_weight


class ObjectBelief:
    __slots__ = ("id", "object_type", "position", "existence", "properties")

    def __init__(
        self,
        object_id: str,
        object_type: str,
        position: Dict[str, BeliefState],
        existence: BeliefState,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = object_id
        self.object_type = object_type
        self.position = position
        self.existence = existence
        self.properties = properties or {}


class ProbabilisticWorldModel(WorldModelStrategy):
    """Physical reasoning strategy using Bayesian belief tracking with per-axis variance and confidence."""
    def __init__(self) -> None:
        self._environment: EnvironmentState = EnvironmentState()
        self._uncertainty: UncertaintyState = UncertaintyState()
        self._beliefs: Dict[str, ObjectBelief] = {}
        self._last_update_cycle: int = 0

    # --- WorldModel interface ---

    @property
    def environment(self) -> EnvironmentState:
        return self._environment

    @property
    def objects(self) -> List[DetectedObject]:
        return [
            DetectedObject(
                id=b.id,
                object_type=b.object_type,
                position={k: vs.mean for k, vs in b.position.items()},
                confidence=b.existence.confidence,
                last_seen_cycle=b.existence.last_updated,
                properties={
                    **b.properties,
                    "variance_x": b.position.get("x", BeliefState()).variance,
                    "variance_y": b.position.get("y", BeliefState()).variance,
                },
            )
            for b in self._beliefs.values()
        ]

    @property
    def uncertainty(self) -> UncertaintyState:
        return self._uncertainty

    @property
    def obstacle_count(self) -> int:
        return sum(
            1 for b in self._beliefs.values()
            if b.object_type == "obstacle" and b.existence.confidence > 0.3
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
        if object_id in self._beliefs:
            belief = self._beliefs[object_id]
            belief.object_type = object_type
            belief.existence = self._bayesian_update(
                belief.existence, confidence, cycle
            )
            for axis, value in position.items():
                if axis in belief.position:
                    belief.position[axis] = self._bayesian_update(
                        belief.position[axis], value, cycle
                    )
                else:
                    belief.position[axis] = BeliefState(
                        mean=value,
                        variance=1.0,
                        confidence=confidence,
                        last_updated=cycle,
                    )
            if properties:
                belief.properties.update(properties)
        else:
            pos_beliefs = {
                k: BeliefState(
                    mean=v,
                    variance=1.0,
                    confidence=confidence,
                    last_updated=cycle,
                )
                for k, v in position.items()
            }
            belief = ObjectBelief(
                object_id=object_id,
                object_type=object_type,
                position=pos_beliefs,
                existence=BeliefState(
                    mean=1.0,
                    variance=1.0,
                    confidence=confidence,
                    last_updated=cycle,
                ),
                properties=properties or {},
            )
            self._beliefs[object_id] = belief

        self._last_update_cycle = cycle

        pos = {k: vs.mean for k, vs in belief.position.items()}
        return DetectedObject(
            id=object_id,
            object_type=object_type,
            position=pos,
            confidence=belief.existence.confidence,
            last_seen_cycle=cycle,
            properties=properties or {},
        )

    def get_object(self, object_id: str) -> Optional[DetectedObject]:
        belief = self._beliefs.get(object_id)
        if belief is None:
            return None
        pos = {k: vs.mean for k, vs in belief.position.items()}
        return DetectedObject(
            id=belief.id,
            object_type=belief.object_type,
            position=pos,
            confidence=belief.existence.confidence,
            last_seen_cycle=belief.existence.last_updated,
            properties={
                **belief.properties,
                "variance_x": belief.position.get("x", BeliefState()).variance,
                "variance_y": belief.position.get("y", BeliefState()).variance,
            },
        )

    def get_objects_by_type(self, object_type: str) -> List[DetectedObject]:
        return [
            self.get_object(bid)
            for bid, b in self._beliefs.items()
            if b.object_type == object_type
        ]

    def remove_stale_objects(self, current_cycle: int, max_age: int = 10) -> int:
        before = len(self._beliefs)
        stale_ids = [
            bid for bid, b in self._beliefs.items()
            if current_cycle - b.existence.last_updated > max_age
        ]
        for sid in stale_ids:
            del self._beliefs[sid]
        return before - len(self._beliefs)

    def remove_object(self, object_id: str) -> bool:
        if object_id not in self._beliefs:
            return False
        del self._beliefs[object_id]
        return True

    def predict(self, steps: int = 1, **kwargs: Any) -> Dict[str, Any]:
        predictions = {}
        for bid, belief in self._beliefs.items():
            if belief.object_type == "obstacle":
                pred_pos = {}
                for axis, bs in belief.position.items():
                    pred_pos[axis] = bs.mean
                predictions[bid] = {
                    "position": pred_pos,
                    "confidence": belief.existence.confidence
                    * max(0.0, 1.0 - 0.1 * steps),
                    "object_type": belief.object_type,
                }
        return {
            "predicted_objects": predictions,
            "method": "bayesian_hold",
            "note": "ProbabilisticWorldModel holds last known position with decayed confidence",
        }

    def serialize(self) -> Dict[str, Any]:
        return {
            "type": "probabilistic",
            "environment": self._environment.model_dump(),
            "beliefs": [
                {
                    "id": b.id,
                    "object_type": b.object_type,
                    "position": {k: {"mean": vs.mean, "variance": vs.variance} for k, vs in b.position.items()},
                    "existence": {"mean": b.existence.mean, "variance": b.existence.variance, "confidence": b.existence.confidence},
                    "properties": dict(b.properties),
                }
                for b in self._beliefs.values()
            ],
            "uncertainty": self._uncertainty.model_dump(),
            "obstacle_count": self.obstacle_count,
            "last_update_cycle": self._last_update_cycle,
        }

    def explain(self) -> str:
        parts = [
            "ProbabilisticWorldModel",
            f"{len(self._beliefs)} objects with Bayesian belief tracking",
        ]
        obstacles = self.obstacle_count
        if obstacles:
            parts.append(f"{obstacles} obstacle(s)")
        high_uncertainty = sum(
            1 for b in self._beliefs.values()
            if any(vs.variance > 2.0 for vs in b.position.values())
        )
        if high_uncertainty:
            parts.append(f"{high_uncertainty} object(s) with high position uncertainty")
        if self.has_sensor_degradation:
            degraded = [k for k, v in self._uncertainty.sensor_health.items() if v < 0.5]
            parts.append(f"sensor degradation: {', '.join(degraded)}")
        return " | ".join(parts)

    # --- Bayesian update ---

    def _bayesian_update(self, prior: BeliefState, measurement: float, cycle: int) -> BeliefState:
        if prior.variance <= 0:
            return prior
        measurement_variance = max(0.1, 1.0 - self._uncertainty.perception + 0.1)
        kalman_gain = prior.variance / (prior.variance + measurement_variance)
        new_mean = prior.mean + kalman_gain * (measurement - prior.mean)
        new_variance = (1.0 - kalman_gain) * prior.variance
        new_confidence = min(1.0, prior.confidence + 0.1)

        return BeliefState(
            mean=new_mean,
            variance=new_variance,
            confidence=new_confidence,
            last_updated=cycle,
            prior_weight=prior.prior_weight,
        )

    # --- query methods ---

    def get_belief(self, object_id: str) -> Optional[ObjectBelief]:
        return self._beliefs.get(object_id)

    def get_uncertainty_at(self, x: float, y: float, radius: float = 1.0) -> float:
        uncertainties = []
        for belief in self._beliefs.values():
            bx = belief.position.get("x", BeliefState()).mean
            by = belief.position.get("y", BeliefState()).mean
            dist = math.sqrt((bx - x) ** 2 + (by - y) ** 2)
            if dist < radius:
                avg_var = sum(vs.variance for vs in belief.position.values()) / max(1, len(belief.position))
                uncertainties.append(avg_var)
        return sum(uncertainties) / max(1, len(uncertainties)) if uncertainties else 0.0
