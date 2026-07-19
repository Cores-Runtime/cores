"""
Physicist — CORES' cognitive node for understanding and predicting physical reality.

Architecture:

Physicist
├── Observation Association   — match new observations to existing tracks
├── Sensor Fusion             — confidence-weighted multi-observation fusion
├── Belief Manager            — update the strategy with fused beliefs
├── Physical Reasoning        — infer causal explanations for observed motion
├── Prediction Engine         — delegate to strategy.predict()
├── Confidence Manager        — decay/boost belief confidence over time
├── Consistency Checker       — detect physical contradictions
├── Explainability            — generate human-readable understanding summary
└── Physical Understanding    — serialized output for RuntimeState

Cognitive loop (every cycle):
  Observe → Associate → Fuse → Update Beliefs → Predict →
  Reason → Check Consistency → Manage Confidence → Explain → Publish
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from cores.interfaces.module import Module, ModuleResult
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.world_model.interface import WorldModelStrategy
from cores.core.world_model.simple_registry import SimpleObjectRegistry


# ---------------------------------------------------------------------------
# Heuristic parameter groups — one per sub-component.
#
# These are temporary. Every threshold here is a candidate model that should
# eventually be replaced by a learned/adaptive strategy (e.g. learned
# association distance, Bayesian motion classification, adaptive confidence).
#
# See ADR 0003 for the full migration plan.
# ---------------------------------------------------------------------------

@dataclass
class AssociationParameters:
    """Heuristic thresholds for ObservationAssociation.

    Future: association_model.predict(observation, tracks) → probability
    """
    distance: float = 3.0


@dataclass
class FusionParameters:
    """Heuristic configuration for SensorFusion.

    Future: learned fusion weights per sensor type.
    """
    position_keys: Tuple[str, ...] = ("x", "y", "z")
    confidence_boost_factor: float = 0.05


@dataclass
class PhysicalReasoningParameters:
    """Hardcoded thresholds for PhysicalReasoning's rule-based classifier.

    Future: motion_classifier.predict(vx, vy, ax, ay, ...) → cause
    """
    speed_stationary_threshold: float = 0.01
    accel_external_force_threshold: float = 2.0
    speed_constant_velocity_min: float = 0.1
    accel_constant_velocity_max: float = 0.5
    vx_gravity_max: float = 0.1
    vy_gravity_min: float = 0.5
    conf_stationary: float = 0.9
    conf_constant_velocity: float = 0.85
    conf_external_force_scale: float = 10.0
    conf_gravity: float = 0.6
    conf_unknown: float = 0.3


@dataclass
class ConsistencyParameters:
    """Hardcoded thresholds for ConsistencyChecker.

    Future: anomaly_detector.predict(state) → List[Issue]
    """
    self_detection_radius: float = 0.01
    impossible_speed_threshold: float = 100.0
    overlap_distance: float = 0.1
    temporal_age_threshold: int = 10
    low_confidence_threshold: float = 0.1


@dataclass
class ConfidenceParameters:
    """Heuristic rates for ConfidenceManager.

    Future: adaptive confidence via online parameter estimation.
    """
    decay_per_cycle: float = 0.02
    boost_per_observation: float = 0.05


@dataclass
class PhysicistHeuristics:
    """Composite of every heuristic parameter group in the Physicist.

    This entire object is a candidate model. When a heuristic subsystem is
    replaced by a learned strategy, its parameter group disappears entirely.
    """
    association: AssociationParameters = field(default_factory=AssociationParameters)
    fusion: FusionParameters = field(default_factory=FusionParameters)
    reasoning: PhysicalReasoningParameters = field(default_factory=PhysicalReasoningParameters)
    consistency: ConsistencyParameters = field(default_factory=ConsistencyParameters)
    confidence: ConfidenceParameters = field(default_factory=ConfidenceParameters)


# ---------------------------------------------------------------------------
# PhysicistConfig — runtime options (NOT heuristics).
# These control *how* the Physicist operates, not *what* it believes.
# ---------------------------------------------------------------------------

@dataclass
class PhysicistConfig:
    """Runtime configuration for the Physicist cognitive node.

    Unlike PhysicistHeuristics, these are permanent structural options
    (logging, debug mode, sensor config) that control how the node operates.
    They are NOT candidate models for learned replacement.
    """
    # Placeholder — runtime options will be added as the Physicist evolves.
    pass


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class PhysicistObservation:
    """
    A single observation from any sensor module.
    Modules create these and pass them to the Physicist for association
    and fusion, rather than writing directly to the strategy.
    """
    __slots__ = (
        "source", "object_id", "object_type", "position",
        "confidence", "cycle", "sensor_type", "properties",
    )

    def __init__(
        self,
        source: str,
        object_id: str,
        object_type: str,
        position: Dict[str, float],
        confidence: float,
        cycle: int,
        sensor_type: str = "unknown",
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.source = source
        self.object_id = object_id
        self.object_type = object_type
        self.position = dict(position)
        self.confidence = confidence
        self.cycle = cycle
        self.sensor_type = sensor_type
        self.properties = properties or {}


class MotionHypothesis:
    """
    A causal explanation for why an object is moving.
    Produced by PhysicalReasoning.
    """
    __slots__ = ("cause", "confidence", "description")

    def __init__(self, cause: str, confidence: float, description: str) -> None:
        self.cause = cause
        self.confidence = confidence
        self.description = description

    CAUSES = (
        "free_motion",
        "external_force",
        "gravity",
        "collision",
        "robot_interaction",
        "sensor_noise",
        "unknown",
    )


class ConsistencyIssue:
    __slots__ = ("severity", "description", "objects_involved")

    def __init__(self, severity: str, description: str, objects_involved: Optional[List[str]] = None) -> None:
        self.severity = severity
        self.description = description
        self.objects_involved = objects_involved or []


# ---------------------------------------------------------------------------
# Sub-components
# ---------------------------------------------------------------------------

class ObservationAssociation:
    """
    Associates new observations to existing tracks using spatial proximity.

    Parameters
    ----------
    params : AssociationParameters, optional
        Heuristic thresholds. Defaults to AssociationParameters().
        Replace with a learned association model in the future.
    """

    def __init__(self, params: Optional[AssociationParameters] = None) -> None:
        p = params or AssociationParameters()
        self._distance = p.distance

    def associate(
        self,
        observations: List[PhysicistObservation],
        strategy: WorldModelStrategy,
    ) -> Dict[str, List[PhysicistObservation]]:
        """
        Returns a mapping from existing track IDs to lists of observations
        that should be associated with them. Observations that don't match
        any existing track are keyed under None.
        """
        result: Dict[str, List[PhysicistObservation]] = {}

        for obs in observations:
            matched_id: Optional[str] = None
            closest_dist = float("inf")

            for existing in strategy.objects:
                ex, ey = existing.position.get("x", 0), existing.position.get("y", 0)
                ox, oy = obs.position.get("x", 0), obs.position.get("y", 0)
                dist = math.sqrt((ex - ox) ** 2 + (ey - oy) ** 2)

                if dist < self._distance and dist < closest_dist:
                    matched_id = existing.id
                    closest_dist = dist

            key = matched_id if matched_id is not None else f"__new__{obs.object_id}"
            if key not in result:
                result[key] = []
            result[key].append(obs)

        return result


class SensorFusion:
    """
    Fuses multiple observations of the same entity into a single belief update
    using confidence-weighted averaging.

    Parameters
    ----------
    params : FusionParameters, optional
        Heuristic configuration. Defaults to FusionParameters().
    """

    def __init__(self, params: Optional[FusionParameters] = None) -> None:
        p = params or FusionParameters()
        self._position_keys = p.position_keys
        self._boost_factor = p.confidence_boost_factor

    def fuse(
        self,
        observations: List[PhysicistObservation],
    ) -> Tuple[Dict[str, float], float, Dict[str, Any]]:
        if not observations:
            return {}, 0.0, {}

        n = len(observations)
        weights = [o.confidence for o in observations]
        total_weight = sum(weights)
        if total_weight <= 0:
            total_weight = 1.0

        fused_position: Dict[str, float] = {}
        for key in self._position_keys:
            vals = [o.position.get(key, 0.0) for o in observations]
            fused_position[key] = sum(v * w for v, w in zip(vals, weights)) / total_weight

        fused_confidence = sum(o.confidence * w for o, w in zip(observations, weights)) / total_weight
        fused_confidence = min(1.0, fused_confidence + self._boost_factor * (n - 1))

        fused_properties: Dict[str, Any] = {}
        for obs in observations:
            fused_properties.update(obs.properties)
        fused_properties["fused_sources"] = list(set(o.source for o in observations))
        fused_properties["fused_count"] = n

        return fused_position, fused_confidence, fused_properties


class PhysicalReasoning:
    """
    Infers causal explanations for observed motion using rule-based
    classification of velocity/acceleration patterns.

    This rule set is a temporary heuristic. The long-term replacement is a
    learned motion classifier that predicts P(cause | trajectory) directly.

    Parameters
    ----------
    params : PhysicalReasoningParameters, optional
        Rule thresholds. Defaults to PhysicalReasoningParameters().
    """

    def __init__(self, params: Optional[PhysicalReasoningParameters] = None) -> None:
        p = params or PhysicalReasoningParameters()
        self._speed_stationary = p.speed_stationary_threshold
        self._accel_external = p.accel_external_force_threshold
        self._speed_const_min = p.speed_constant_velocity_min
        self._accel_const_max = p.accel_constant_velocity_max
        self._vx_gravity_max = p.vx_gravity_max
        self._vy_gravity_min = p.vy_gravity_min
        self._c_stationary = p.conf_stationary
        self._c_constant = p.conf_constant_velocity
        self._c_ext_scale = p.conf_external_force_scale
        self._c_gravity = p.conf_gravity
        self._c_unknown = p.conf_unknown

    def infer(
        self,
        track_id: str,
        strategy: WorldModelStrategy,
    ) -> MotionHypothesis:
        obj = strategy.get_object(track_id)
        if obj is None:
            return MotionHypothesis("unknown", 0.0, "object not found")

        props = obj.properties
        vx = props.get("vx", 0.0)
        vy = props.get("vy", 0.0)
        speed = math.sqrt(vx ** 2 + vy ** 2)

        if speed < self._speed_stationary:
            return MotionHypothesis("free_motion", self._c_stationary, f"{track_id} is stationary")

        vx_prev = props.get("vx_prev", vx)
        vy_prev = props.get("vy_prev", vy)
        accel = math.sqrt((vx - vx_prev) ** 2 + (vy - vy_prev) ** 2)

        if accel > self._accel_external:
            return MotionHypothesis(
                "external_force",
                min(0.8, accel / self._c_ext_scale),
                f"{track_id} accelerating at {accel:.1f} m/s² — external force likely",
            )

        if speed > self._speed_const_min and accel < self._accel_const_max:
            return MotionHypothesis(
                "free_motion",
                self._c_constant,
                f"{track_id} moving at {speed:.1f} m/s — constant velocity motion",
            )

        if abs(vx) < self._vx_gravity_max and abs(vy) > self._vy_gravity_min:
            return MotionHypothesis(
                "gravity",
                self._c_gravity,
                f"{track_id} descending — gravity likely cause",
            )

        return MotionHypothesis("unknown", self._c_unknown, f"{track_id} motion cause unclear")

    def infer_all(
        self,
        strategy: WorldModelStrategy,
    ) -> Dict[str, MotionHypothesis]:
        hypotheses: Dict[str, MotionHypothesis] = {}
        for obj in strategy.objects:
            hypotheses[obj.id] = self.infer(obj.id, strategy)
        return hypotheses


class ConsistencyChecker:
    """
    Detects physical inconsistencies in the current understanding.

    Checks are additive — new checks can be added without affecting existing ones.
    The long-term replacement is an anomaly detector that learns what
    "physically consistent" looks like from data.

    Parameters
    ----------
    params : ConsistencyParameters, optional
        Detection thresholds. Defaults to ConsistencyParameters().
    """

    def __init__(self, params: Optional[ConsistencyParameters] = None) -> None:
        p = params or ConsistencyParameters()
        self._self_det_radius = p.self_detection_radius
        self._impossible_speed = p.impossible_speed_threshold
        self._overlap_dist = p.overlap_distance
        self._temporal_age = p.temporal_age_threshold
        self._low_conf = p.low_confidence_threshold

    def check(self, strategy: WorldModelStrategy) -> List[ConsistencyIssue]:
        issues: List[ConsistencyIssue] = []

        issues.extend(self._check_self_detection(strategy))
        issues.extend(self._check_impossible_speed(strategy))
        issues.extend(self._check_object_overlap(strategy))
        issues.extend(self._check_temporal_consistency(strategy))

        return issues

    def _check_self_detection(self, strategy: WorldModelStrategy) -> List[ConsistencyIssue]:
        issues: List[ConsistencyIssue] = []
        for obj in strategy.objects:
            if obj.object_type == "robot":
                continue
            pos = obj.position
            if abs(pos.get("x", 0)) < self._self_det_radius and abs(pos.get("y", 0)) < self._self_det_radius:
                issues.append(ConsistencyIssue(
                    severity="warning",
                    description=f"{obj.id} at origin — possible self-detection",
                    objects_involved=[obj.id],
                ))
        return issues

    def _check_impossible_speed(self, strategy: WorldModelStrategy) -> List[ConsistencyIssue]:
        issues: List[ConsistencyIssue] = []
        for obj in strategy.objects:
            props = obj.properties
            vx = props.get("vx", 0.0)
            vy = props.get("vy", 0.0)
            speed = math.sqrt(vx ** 2 + vy ** 2)
            if speed > self._impossible_speed:
                issues.append(ConsistencyIssue(
                    severity="error",
                    description=f"{obj.id} impossible speed {speed:.1f} m/s",
                    objects_involved=[obj.id],
                ))
        return issues

    def _check_object_overlap(self, strategy: WorldModelStrategy) -> List[ConsistencyIssue]:
        issues: List[ConsistencyIssue] = []
        objects = list(strategy.objects)
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                a, b = objects[i], objects[j]
                dx = a.position.get("x", 0) - b.position.get("x", 0)
                dy = a.position.get("y", 0) - b.position.get("y", 0)
                dist = math.sqrt(dx ** 2 + dy ** 2)
                if dist < self._overlap_dist and dist > 0:
                    issues.append(ConsistencyIssue(
                        severity="warning",
                        description=f"{a.id} and {b.id} overlapping — possible duplicate",
                        objects_involved=[a.id, b.id],
                    ))
        return issues

    def _check_temporal_consistency(self, strategy: WorldModelStrategy) -> List[ConsistencyIssue]:
        issues: List[ConsistencyIssue] = []
        for obj in strategy.objects:
            age = strategy.last_update_cycle - obj.last_seen_cycle
            if age > self._temporal_age and obj.confidence > 0.5:
                issues.append(ConsistencyIssue(
                    severity="info",
                    description=f"{obj.id} unseen for {age} cycles but still high confidence",
                    objects_involved=[obj.id],
                ))
            if obj.confidence < self._low_conf and obj.object_type == "obstacle":
                issues.append(ConsistencyIssue(
                    severity="info",
                    description=f"{obj.id} extremely low confidence — consider removal",
                    objects_involved=[obj.id],
                ))
        return issues


class ConfidenceManager:
    """
    Manages belief confidence over time using fixed decay/boost rates.

    These rates are heuristic. The long-term replacement is adaptive confidence
    via online parameter estimation (e.g. Bayesian optimisation over a
    consistency reward signal).

    Parameters
    ----------
    params : ConfidenceParameters, optional
        Decay/boost rates. Defaults to ConfidenceParameters().
    """

    def __init__(self, params: Optional[ConfidenceParameters] = None) -> None:
        p = params or ConfidenceParameters()
        self._decay_per_cycle = p.decay_per_cycle
        self._boost_per_observation = p.boost_per_observation

    def decay(self, strategy: WorldModelStrategy, current_cycle: int) -> None:
        for obj in strategy.objects:
            age = current_cycle - obj.last_seen_cycle
            if age > 0:
                decay = self._decay_per_cycle * age
                obj.confidence = max(0.0, obj.confidence - decay)

    def boost(self, strategy: WorldModelStrategy, object_id: str) -> None:
        obj = strategy.get_object(object_id)
        if obj is not None:
            obj.confidence = min(1.0, obj.confidence + self._boost_per_observation)


# ---------------------------------------------------------------------------
# Physicist — the main cognitive node
# ---------------------------------------------------------------------------

class Physicist(Module):
    """
    The Physicist is the cognitive node responsible for maintaining CORES'
    understanding of physical reality.

    It owns a WorldModelStrategy that transforms streaming observations into
    a coherent, predictive, uncertainty-aware physical representation.

    Cognitive loop (executed every cycle after all observation modules):
      1. Observe          — collect observations from the observation buffer
      2. Associate        — match observations to existing strategy tracks
      3. Fuse             — confidence-weighted fusion of matched observations
      4. Update Beliefs   — push fused observations into the strategy
      5. Predict          — estimate future physical states
      6. Reason           — infer causal explanations for motion
      7. Check Consistency — detect contradictions in current beliefs
      8. Manage Confidence — decay/boost belief confidence
      9. Explain          — generate human-readable understanding summary
     10. Publish          — make understanding available via RuntimeState
    """

    def __init__(
        self,
        name: str = "physicist",
        strategy: Optional[WorldModelStrategy] = None,
        heuristics: Optional[PhysicistHeuristics] = None,
        config: Optional[PhysicistConfig] = None,
    ) -> None:
        super().__init__(name)
        self._heuristics = heuristics or PhysicistHeuristics()
        self._config = config or PhysicistConfig()
        self._strategy: WorldModelStrategy = strategy or SimpleObjectRegistry()
        self._observation_buffer: List[PhysicistObservation] = []
        self._prediction_cache: Dict[str, Any] = {}
        self._motion_hypotheses: Dict[str, MotionHypothesis] = {}
        self._consistency_issues: List[ConsistencyIssue] = []
        self._last_explanation: str = ""

        self._associator = ObservationAssociation(self._heuristics.association)
        self._fuser = SensorFusion(self._heuristics.fusion)
        self._reasoner = PhysicalReasoning(self._heuristics.reasoning)
        self._checker = ConsistencyChecker(self._heuristics.consistency)
        self._confidence_mgr = ConfidenceManager(self._heuristics.confidence)

    # --- properties ---

    @property
    def strategy(self) -> WorldModelStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, s: WorldModelStrategy) -> None:
        self._strategy = s

    @property
    def physical_understanding(self) -> Dict[str, Any]:
        return self._strategy.serialize()

    @property
    def last_explanation(self) -> str:
        return self._last_explanation

    @property
    def motion_hypotheses(self) -> Dict[str, MotionHypothesis]:
        return dict(self._motion_hypotheses)

    @property
    def consistency_issues(self) -> List[ConsistencyIssue]:
        return list(self._consistency_issues)

    # --- observation pipeline ---

    def ingest_observation(self, observation: PhysicistObservation) -> None:
        self._observation_buffer.append(observation)

    def ingest_observations(self, observations: List[PhysicistObservation]) -> None:
        self._observation_buffer.extend(observations)

    def clear_observation_buffer(self) -> None:
        self._observation_buffer.clear()

    # --- cognitive loop ---

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        metrics: Dict[str, Any] = {}

        # 1. Associate observations to existing tracks
        pending = list(self._observation_buffer)
        self._observation_buffer.clear()

        associated = self._associator.associate(pending, self._strategy)
        metrics["observations_received"] = len(pending)
        metrics["observations_associated"] = sum(
            len(obs_list) for key, obs_list in associated.items()
            if not key.startswith("__new__")
        )

        # 2. Fuse and update beliefs
        for key, obs_list in associated.items():
            if key.startswith("__new__"):
                obs = obs_list[0]
                fused_pos, fused_conf, fused_props = self._fuser.fuse(obs_list)
                self._strategy.upsert_object(
                    object_id=obs.object_id,
                    object_type=obs.object_type,
                    position=fused_pos,
                    confidence=fused_conf,
                    cycle=obs.cycle,
                    properties=fused_props,
                )
            else:
                fused_pos, fused_conf, fused_props = self._fuser.fuse(obs_list)
                existing = self._strategy.get_object(key)
                if existing is not None:
                    merged_props = dict(existing.properties)
                    merged_props.update(fused_props)
                    self._strategy.upsert_object(
                        object_id=key,
                        object_type=existing.object_type,
                        position=fused_pos,
                        confidence=fused_conf,
                        cycle=obs_list[0].cycle,
                        properties=merged_props,
                    )

        # 3. Predict future state
        prediction = self._strategy.predict(steps=1)
        self._prediction_cache = prediction
        metrics["prediction"] = prediction.get("method", "none")

        # 4. Reason about causes of motion
        old_velocities: Dict[str, Tuple[float, float]] = {}
        for obj in self._strategy.objects:
            props = obj.properties
            vx = props.get("vx", 0.0)
            vy = props.get("vy", 0.0)
            old_velocities[obj.id] = (
                props.get("vx_prev", vx),
                props.get("vy_prev", vy),
            )
            props["vx_prev"] = vx
            props["vy_prev"] = vy

        self._motion_hypotheses = self._reasoner.infer_all(self._strategy)
        metrics["objects_with_motion_hypothesis"] = len(self._motion_hypotheses)

        # 5. Check consistency
        self._consistency_issues = self._checker.check(self._strategy)
        metrics["consistency_issues"] = len(self._consistency_issues)
        error_count = sum(1 for i in self._consistency_issues if i.severity == "error")
        metrics["consistency_errors"] = error_count

        # 6. Manage confidence
        self._confidence_mgr.decay(self._strategy, context.cycle_count)

        # 7. Generate explanation
        self._last_explanation = self._generate_explanation()
        metrics["explanation_length"] = len(self._last_explanation)

        # 8. Track key indicators
        metrics["obstacle_count"] = self._strategy.obstacle_count
        metrics["objects_tracked"] = len(self._strategy.objects)
        metrics["has_sensor_degradation"] = self._strategy.has_sensor_degradation
        metrics["strategy_type"] = type(self._strategy).__name__
        metrics["strategy_last_update"] = self._strategy.last_update_cycle

        return ModuleResult(
            module_name=self.name,
            status="SUCCESS",
            metrics=metrics,
            execution_time_ms=0.0,
        )

    # --- explanation ---

    def _generate_explanation(self) -> str:
        parts: List[str] = []
        strategy_name = type(self._strategy).__name__
        parts.append(f"Physicist [{strategy_name}]")

        obs_count = self._strategy.obstacle_count
        total = len(self._strategy.objects)
        parts.append(f"{obs_count} obstacle(s) / {total} object(s)")

        env = self._strategy.environment
        parts.append(f"terrain={env.terrain}, weather={env.weather}")

        moving = sum(
            1 for h in self._motion_hypotheses.values()
            if h.cause != "free_motion"
        )
        if moving:
            causes = set(h.cause for h in self._motion_hypotheses.values() if h.cause != "free_motion")
            parts.append(f"{moving} moving ({', '.join(sorted(causes))})")

        if self._strategy.has_sensor_degradation:
            degraded = [
                k for k, v in self._strategy.uncertainty.sensor_health.items()
                if v < 0.5
            ]
            parts.append(f"sensor degradation: {', '.join(degraded)}")

        errors = sum(1 for i in self._consistency_issues if i.severity == "error")
        warnings = sum(1 for i in self._consistency_issues if i.severity == "warning")
        if errors or warnings:
            parts.append(f"inconsistencies: {errors} error(s), {warnings} warning(s)")

        obstacles_predicted = self._prediction_cache.get("predicted_objects", {})
        if obstacles_predicted:
            parts.append(f"predicting {len(obstacles_predicted)} object(s)")

        return " | ".join(parts)

    # --- forwarded strategy access ---

    def upsert_object(self, *args: Any, **kwargs: Any) -> Any:
        return self._strategy.upsert_object(*args, **kwargs)

    def get_object(self, *args: Any, **kwargs: Any) -> Any:
        return self._strategy.get_object(*args, **kwargs)

    def get_objects_by_type(self, *args: Any, **kwargs: Any) -> Any:
        return self._strategy.get_objects_by_type(*args, **kwargs)

    def update_environment(self, *args: Any, **kwargs: Any) -> None:
        self._strategy.update_environment(*args, **kwargs)

    def remove_stale_objects(self, *args: Any, **kwargs: Any) -> int:
        return self._strategy.remove_stale_objects(*args, **kwargs)
