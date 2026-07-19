import math
import pytest
from cores.core import (
    StateEstimation, SimpleObjectRegistry, SSKPM, Runtime, Scheduler,
    DefaultSchedulingPolicy, ExecutionLayer, WorldModel, WorldModelStrategy,
    ProbabilisticWorldModel, DynamicTrackingWorldModel, SemanticWorldModel,
)
from cores.core.state_estimation import (
    StateEstimationHeuristics, AssociationParameters, FusionParameters,
    PhysicalReasoningParameters, ConsistencyParameters, ConfidenceParameters,
    StateEstimationObservation, ObservationAssociation, SensorFusion,
    PhysicalReasoning, ConsistencyChecker, ConfidenceManager,
    MotionHypothesis, ConsistencyIssue,
)
from cores.interfaces.module import Module, ModuleResult
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


# =========================================================================
# Data types
# =========================================================================

class TestStateEstimationObservation:
    def test_default_creation(self):
        obs = StateEstimationObservation(
            source="camera", object_id="obj_1", object_type="obstacle",
            position={"x": 1, "y": 2}, confidence=0.9, cycle=1,
        )
        assert obs.source == "camera"
        assert obs.object_id == "obj_1"
        assert obs.position == {"x": 1, "y": 2}
        assert obs.confidence == 0.9
        assert obs.cycle == 1
        assert obs.sensor_type == "unknown"

    def test_with_sensor_type(self):
        obs = StateEstimationObservation(
            source="lidar", object_id="o1", object_type="obstacle",
            position={"x": 0, "y": 0}, confidence=0.8, cycle=2,
            sensor_type="lidar",
        )
        assert obs.sensor_type == "lidar"

    def test_with_properties(self):
        obs = StateEstimationObservation(
            source="depth", object_id="o1", object_type="obstacle",
            position={"x": 5, "y": 5}, confidence=0.7, cycle=3,
            properties={"color": "red"},
        )
        assert obs.properties["color"] == "red"

    def test_attributes_mutable(self):
        obs = StateEstimationObservation("cam", "o1", "obstacle", {"x": 1, "y": 2}, 0.9, 1)
        assert obs.source == "cam"
        obs.source = "lidar"
        assert obs.source == "lidar"


class TestMotionHypothesis:
    def test_has_cause_constants(self):
        assert "free_motion" in MotionHypothesis.CAUSES
        assert "external_force" in MotionHypothesis.CAUSES
        assert "gravity" in MotionHypothesis.CAUSES
        assert "collision" in MotionHypothesis.CAUSES
        assert "unknown" in MotionHypothesis.CAUSES

    def test_creation(self):
        h = MotionHypothesis("free_motion", 0.9, "object is stationary")
        assert h.cause == "free_motion"
        assert h.confidence == 0.9
        assert h.description == "object is stationary"


class TestConsistencyIssue:
    def test_creation(self):
        issue = ConsistencyIssue("error", "test issue", ["obj_1"])
        assert issue.severity == "error"
        assert issue.description == "test issue"
        assert issue.objects_involved == ["obj_1"]

    def test_default_objects(self):
        issue = ConsistencyIssue("info", "no objects")
        assert issue.objects_involved == []

    def test_properties(self):
        issue = ConsistencyIssue("warning", "overlap detected", ["a", "b"])
        assert issue.severity == "warning"
        assert issue.description == "overlap detected"
        assert issue.objects_involved == ["a", "b"]


# =========================================================================
# ObservationAssociation
# =========================================================================

class TestObservationAssociation:
    def test_no_observations(self):
        strategy = SimpleObjectRegistry()
        associator = ObservationAssociation()
        result = associator.associate([], strategy)
        assert result == {}

    def test_no_existing_tracks(self):
        strategy = SimpleObjectRegistry()
        associator = ObservationAssociation()
        obs = StateEstimationObservation("cam", "new_obj", "obstacle", {"x": 5, "y": 5}, 0.9, 1)
        result = associator.associate([obs], strategy)
        assert any(k.startswith("__new__") for k in result.keys())

    def test_associates_to_closest_track(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("existing_1", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        strategy.upsert_object("existing_2", "obstacle", {"x": 50, "y": 50}, 0.9, cycle=1)

        associator = ObservationAssociation(AssociationParameters(distance=10.0))
        obs = StateEstimationObservation("cam", "new_obs", "obstacle", {"x": 5.5, "y": 5.5}, 0.9, 2)
        result = associator.associate([obs], strategy)

        assert "existing_1" in result
        assert "existing_2" not in result

    def test_out_of_range_not_associated(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("far", "obstacle", {"x": 100, "y": 100}, 0.9, cycle=1)

        associator = ObservationAssociation(AssociationParameters(distance=5.0))
        obs = StateEstimationObservation("cam", "far_obs", "obstacle", {"x": 0, "y": 0}, 0.9, 2)
        result = associator.associate([obs], strategy)

        assert "far" not in result
        assert any(k.startswith("__new__") for k in result.keys())

    def test_multiple_observations_same_track(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("target", "obstacle", {"x": 10, "y": 10}, 0.9, cycle=1)

        associator = ObservationAssociation(AssociationParameters(distance=5.0))
        obs1 = StateEstimationObservation("cam", "obs_a", "obstacle", {"x": 11, "y": 10}, 0.8, 2)
        obs2 = StateEstimationObservation("lidar", "obs_b", "obstacle", {"x": 10.5, "y": 9.5}, 0.9, 2)
        result = associator.associate([obs1, obs2], strategy)

        assert "target" in result
        assert len(result["target"]) == 2

    def test_multiple_tracks_multiple_observations(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("a", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        strategy.upsert_object("b", "obstacle", {"x": 20, "y": 20}, 0.9, cycle=1)

        associator = ObservationAssociation(AssociationParameters(distance=5.0))
        obs_a = StateEstimationObservation("cam", "obs_a", "obstacle", {"x": 0.5, "y": 0.5}, 0.8, 2)
        obs_b = StateEstimationObservation("lidar", "obs_b", "obstacle", {"x": 20.5, "y": 19.5}, 0.9, 2)
        result = associator.associate([obs_a, obs_b], strategy)

        assert "a" in result
        assert "b" in result
        assert len(result["a"]) == 1
        assert len(result["b"]) == 1

    def test_new_track_outside_range(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("far", "obstacle", {"x": 50, "y": 50}, 0.9, cycle=1)
        associator = ObservationAssociation(AssociationParameters(distance=1.0))
        obs = StateEstimationObservation("cam", "new_id", "obstacle", {"x": 100, "y": 100}, 0.9, 2)
        result = associator.associate([obs], strategy)
        assert "far" not in result
        assert "__new__new_id" in result


# =========================================================================
# SensorFusion
# =========================================================================

class TestSensorFusion:
    def test_empty(self):
        fuser = SensorFusion()
        pos, conf, props = fuser.fuse([])
        assert pos == {}
        assert conf == 0.0
        assert props == {}

    def test_single_observation(self):
        fuser = SensorFusion()
        obs = StateEstimationObservation("cam", "o1", "obstacle", {"x": 5, "y": 10}, 0.9, 1)
        pos, conf, props = fuser.fuse([obs])
        assert pos["x"] == 5
        assert pos["y"] == 10
        assert conf == 0.9

    def test_confidence_weighted_average(self):
        fuser = SensorFusion()
        obs1 = StateEstimationObservation("cam", "o1", "obstacle", {"x": 5, "y": 10}, 0.9, 1)
        obs2 = StateEstimationObservation("lidar", "o1", "obstacle", {"x": 6, "y": 11}, 0.5, 1)
        pos, conf, props = fuser.fuse([obs1, obs2])
        expected_x = (5 * 0.9 + 6 * 0.5) / 1.4
        expected_y = (10 * 0.9 + 11 * 0.5) / 1.4
        assert abs(pos["x"] - expected_x) < 1e-6
        assert abs(pos["y"] - expected_y) < 1e-6

    def test_fused_confidence_boost(self):
        fuser = SensorFusion()
        obs1 = StateEstimationObservation("cam", "o1", "obstacle", {"x": 0, "y": 0}, 0.7, 1)
        obs2 = StateEstimationObservation("lidar", "o1", "obstacle", {"x": 0, "y": 0}, 0.7, 1)
        _, conf, _ = fuser.fuse([obs1, obs2])
        assert conf > 0.7
        assert conf <= 1.0

    def test_fused_sources_tracked(self):
        fuser = SensorFusion()
        obs1 = StateEstimationObservation("camera", "o1", "obstacle", {"x": 1, "y": 1}, 0.8, 1)
        obs2 = StateEstimationObservation("lidar", "o1", "obstacle", {"x": 1, "y": 1}, 0.9, 1)
        _, _, props = fuser.fuse([obs1, obs2])
        assert "camera" in props["fused_sources"]
        assert "lidar" in props["fused_sources"]
        assert props["fused_count"] == 2

    def test_three_observations_fusion(self):
        fuser = SensorFusion()
        obs = [
            StateEstimationObservation("a", "o1", "obstacle", {"x": 10, "y": 20}, 0.8, 1),
            StateEstimationObservation("b", "o1", "obstacle", {"x": 11, "y": 19}, 0.7, 1),
            StateEstimationObservation("c", "o1", "obstacle", {"x": 10.5, "y": 20.5}, 0.9, 1),
        ]
        pos, conf, props = fuser.fuse(obs)
        assert "x" in pos
        assert "y" in pos
        assert conf > 0.7
        assert props["fused_count"] == 3

    def test_different_keys_across_observations(self):
        fuser = SensorFusion()
        obs1 = StateEstimationObservation("a", "o1", "obstacle", {"x": 1, "y": 2}, 0.8, 1)
        obs2 = StateEstimationObservation("b", "o1", "obstacle", {"x": 3, "z": 4}, 0.8, 1)
        pos, _, _ = fuser.fuse([obs1, obs2])
        assert "x" in pos
        assert "y" in pos
        assert "z" in pos


# =========================================================================
# PhysicalReasoning
# =========================================================================

class TestPhysicalReasoning:
    def test_nonexistent_object(self):
        strategy = SimpleObjectRegistry()
        reasoner = PhysicalReasoning()
        h = reasoner.infer("nonexistent", strategy)
        assert h.cause == "unknown"

    def test_stationary_object(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("static", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        reasoner = PhysicalReasoning()
        h = reasoner.infer("static", strategy)
        assert h.cause == "free_motion"
        assert "stationary" in h.description

    def test_constant_velocity(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("moving", "obstacle", {"x": 0, "y": 0}, 0.9,
                                cycle=1, properties={"vx": 5, "vy": 3})
        reasoner = PhysicalReasoning()
        h = reasoner.infer("moving", strategy)
        assert h.cause == "free_motion"
        assert "constant velocity" in h.description

    def test_accelerating_object(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("accel", "obstacle", {"x": 0, "y": 0}, 0.9,
                                cycle=2, properties={"vx": 10, "vy": 0, "vx_prev": 0, "vy_prev": 0})
        reasoner = PhysicalReasoning()
        h = reasoner.infer("accel", strategy)
        assert h.cause == "external_force"
        assert "accelerating" in h.description

    def test_gravity_hypothesis(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("falling", "obstacle", {"x": 0, "y": 0}, 0.9,
                                cycle=1, properties={"vx": 0, "vy": 0.8,
                                                       "vx_prev": 0, "vy_prev": 0})
        reasoner = PhysicalReasoning()
        h = reasoner.infer("falling", strategy)
        assert h.cause == "gravity"
        assert "descending" in h.description

    def test_constant_velocity_rising(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("rising", "obstacle", {"x": 0, "y": 0}, 0.9,
                                cycle=1, properties={"vx": 0, "vy": -10})
        reasoner = PhysicalReasoning()
        h = reasoner.infer("rising", strategy)
        assert h.cause == "free_motion"
        assert "constant velocity" in h.description

    def test_infer_all(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("a", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        strategy.upsert_object("b", "obstacle", {"x": 1, "y": 1}, 0.9, cycle=1,
                                properties={"vx": 5, "vy": 0})
        reasoner = PhysicalReasoning()
        hypotheses = reasoner.infer_all(strategy)
        assert "a" in hypotheses
        assert "b" in hypotheses
        assert hypotheses["a"].cause == "free_motion"

    def test_empty_strategy(self):
        reasoner = PhysicalReasoning()
        hypotheses = reasoner.infer_all(SimpleObjectRegistry())
        assert hypotheses == {}


# =========================================================================
# ConfidenceManager
# =========================================================================

class TestConfidenceManager:
    def test_decay_reduces_confidence(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("test", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        mgr = ConfidenceManager(ConfidenceParameters(decay_per_cycle=0.1))
        mgr.decay(strategy, current_cycle=5)
        obj = strategy.get_object("test")
        assert obj is not None
        assert obj.confidence < 0.9

    def test_decay_over_multiple_cycles(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("test", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        mgr = ConfidenceManager(ConfidenceParameters(decay_per_cycle=0.2))
        mgr.decay(strategy, current_cycle=5)
        obj = strategy.get_object("test")
        assert obj is not None
        assert obj.confidence < 0.5

    def test_decay_does_not_go_below_zero(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("test", "obstacle", {"x": 0, "y": 0}, 0.1, cycle=1)
        mgr = ConfidenceManager(ConfidenceParameters(decay_per_cycle=0.5))
        mgr.decay(strategy, current_cycle=100)
        obj = strategy.get_object("test")
        assert obj is not None
        assert obj.confidence >= 0.0

    def test_boost_increases_confidence(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("test", "obstacle", {"x": 0, "y": 0}, 0.5, cycle=1)
        mgr = ConfidenceManager(ConfidenceParameters(boost_per_observation=0.3))
        mgr.boost(strategy, "test")
        obj = strategy.get_object("test")
        assert obj is not None
        assert obj.confidence == 0.8

    def test_boost_does_not_exceed_one(self):
        strategy = SimpleObjectRegistry()
        strategy.upsert_object("test", "obstacle", {"x": 0, "y": 0}, 0.95, cycle=1)
        mgr = ConfidenceManager(ConfidenceParameters(boost_per_observation=0.1))
        mgr.boost(strategy, "test")
        obj = strategy.get_object("test")
        assert obj is not None
        assert obj.confidence <= 1.0

    def test_boost_nonexistent_no_error(self):
        strategy = SimpleObjectRegistry()
        mgr = ConfidenceManager()
        mgr.boost(strategy, "nonexistent")


# =========================================================================
# StateEstimation — main cognitive node
# =========================================================================

class TestStateEstimationCreation:
    def test_default_creation(self):
        p = StateEstimation()
        assert p.name == "state_estimation"
        assert isinstance(p.strategy, SimpleObjectRegistry)

    def test_custom_strategy(self):
        p = StateEstimation(strategy=SSKPM())
        assert isinstance(p.strategy, SSKPM)

    def test_custom_name(self):
        p = StateEstimation(name="my_physicist")
        assert p.name == "my_physicist"

    def test_sub_components_created(self):
        p = StateEstimation()
        assert hasattr(p, "_associator")
        assert hasattr(p, "_fuser")
        assert hasattr(p, "_reasoner")
        assert hasattr(p, "_checker")
        assert hasattr(p, "_confidence_mgr")


class TestStateEstimationObservationPipeline:
    def test_ingest_single_observation(self):
        p = StateEstimation()
        obs = StateEstimationObservation("camera", "test_obj", "obstacle", {"x": 5, "y": 5}, 0.9, 1)
        p.ingest_observation(obs)
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert result.metrics["observations_received"] == 1

    def test_ingest_multiple_observations(self):
        p = StateEstimation()
        obs = [
            StateEstimationObservation("cam", "o1", "obstacle", {"x": 1, "y": 1}, 0.8, 1),
            StateEstimationObservation("lidar", "o2", "obstacle", {"x": 2, "y": 2}, 0.9, 1),
        ]
        p.ingest_observations(obs)
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert result.metrics["observations_received"] == 2

    def test_observation_buffer_cleared_after_execute(self):
        p = StateEstimation()
        obs = StateEstimationObservation("cam", "o1", "obstacle", {"x": 1, "y": 1}, 0.8, 1)
        p.ingest_observation(obs)
        state = RobotState()
        context = RuntimeContext()
        p.execute(state, context)
        assert len(p._observation_buffer) == 0

    def test_observation_results_in_obstacle(self):
        p = StateEstimation()
        obs = StateEstimationObservation("cam", "obs_1", "obstacle", {"x": 10, "y": 20}, 0.9, 1)
        p.ingest_observation(obs)
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert result.metrics["obstacle_count"] >= 1
        assert p.strategy.get_object("obs_1") is not None

    def test_fused_observations_create_single_track(self):
        p = StateEstimation()
        p.ingest_observations([
            StateEstimationObservation("cam", "target", "obstacle", {"x": 5, "y": 5}, 0.8, 1),
            StateEstimationObservation("lidar", "target", "obstacle", {"x": 5.5, "y": 4.5}, 0.9, 1),
        ])
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert result.metrics["obstacle_count"] == 1

    def test_clear_observation_buffer(self):
        p = StateEstimation()
        p.ingest_observation(StateEstimationObservation("cam", "o1", "obstacle", {"x": 0, "y": 0}, 0.8, 1))
        p.clear_observation_buffer()
        assert len(p._observation_buffer) == 0


class TestStateEstimationCognitiveLoop:
    def test_execute_returns_module_result(self):
        p = StateEstimation()
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert result.module_name == "state_estimation"
        assert result.status == "SUCCESS"

    def test_execute_contains_all_metrics(self):
        p = StateEstimation()
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert "observations_received" in result.metrics
        assert "observations_associated" in result.metrics
        assert "prediction" in result.metrics
        assert "objects_with_motion_hypothesis" in result.metrics
        assert "consistency_issues" in result.metrics
        assert "consistency_errors" in result.metrics
        assert "obstacle_count" in result.metrics
        assert "objects_tracked" in result.metrics
        assert "strategy_type" in result.metrics

    def test_prediction_cache_populated(self):
        p = StateEstimation()
        state = RobotState()
        context = RuntimeContext()
        p.execute(state, context)
        assert "method" in p._prediction_cache

    def test_motion_hypotheses_populated(self):
        p = StateEstimation()
        p.strategy.upsert_object("test", "obstacle", {"x": 1, "y": 1}, 0.9, cycle=1)
        state = RobotState()
        context = RuntimeContext()
        p.execute(state, context)
        assert "test" in p.motion_hypotheses

    def test_consistency_issues_property(self):
        p = StateEstimation()
        p.strategy.upsert_object("at_origin", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        state = RobotState()
        context = RuntimeContext()
        p.execute(state, context)
        assert len(p.consistency_issues) > 0

    def test_explanation_generated(self):
        p = StateEstimation()
        state = RobotState()
        context = RuntimeContext()
        p.execute(state, context)
        assert "StateEstimation" in p.last_explanation
        assert len(p.last_explanation) > 10

    def test_explanation_includes_observations(self):
        p = StateEstimation()
        p.strategy.upsert_object("shown", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        p.strategy.upsert_object("moving_target", "obstacle", {"x": 10, "y": 10}, 0.9,
                                  cycle=1, properties={"vx": 2, "vy": 3})
        state = RobotState()
        context = RuntimeContext()
        p.execute(state, context)
        expl = p.last_explanation
        assert "2 obstacle(s)" in expl or "obstacle" in expl


class TestStateEstimationRuntimeIntegration:
    def test_runtime_has_state_estimation(self):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer)
        assert hasattr(runtime, "state_estimation")
        assert runtime.state_estimation is not None

    def test_runtime_wires_strategy_to_context(self):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer)
        assert runtime.context.world_model is None
        runtime.step()
        assert runtime.context.world_model is runtime.state_estimation.strategy

    def test_state_estimation_runs_after_modules(self):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer)

        class Observer(Module):
            def execute(self, state, context):
                context.world_model.upsert_object("obs_result", "obstacle",
                    {"x": 5, "y": 5}, 0.95, cycle=context.cycle_count)
                return ModuleResult(module_name=self.name)

        runtime.register_module(Observer("observer"))
        runtime.step()
        assert runtime.state_estimation.strategy.obstacle_count == 1
        obj = runtime.state_estimation.strategy.get_object("obs_result")
        assert obj is not None
        assert obj.confidence == 0.95

    def test_state_estimation_strategy_swappable(self):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer, world_model=SSKPM())
        assert isinstance(runtime.state_estimation.strategy, SSKPM)

    def test_multiple_steps_persistent_understanding(self):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer)

        class Writer(Module):
            def execute(self, state, context):
                context.world_model.upsert_object("persistent", "obstacle",
                    {"x": 1, "y": 1}, 0.9, cycle=context.cycle_count)
                return ModuleResult(module_name=self.name)

        runtime.register_module(Writer("writer"))
        for _ in range(5):
            runtime.step()
        assert runtime.state_estimation.strategy.obstacle_count >= 1

    def test_state_estimation_explanation_in_snapshot(self):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer)
        runtime.step()
        snapshot = runtime.bridge.snapshot()
        assert snapshot is not None
        assert len(snapshot.explainability.module_changes) > 0

    def test_state_estimation_understanding_in_snapshot(self):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer)

        class Writer(Module):
            def execute(self, state, context):
                context.world_model.upsert_object("snap_obj", "obstacle",
                    {"x": 3, "y": 7}, 0.88, cycle=context.cycle_count)
                return ModuleResult(module_name=self.name)

        runtime.register_module(Writer("w"))
        runtime.step()
        snapshot = runtime.bridge.snapshot()
        assert snapshot is not None
        assert snapshot.world_model.obstacle_count >= 1


class TestStateEstimationForwardedMethods:
    def test_upsert_forwarded(self):
        p = StateEstimation()
        obj = p.upsert_object("fwd_1", "obstacle", {"x": 3, "y": 4}, 0.9, cycle=1)
        assert obj.id == "fwd_1"
        assert p.strategy.get_object("fwd_1") is not None

    def test_get_object_forwarded(self):
        p = StateEstimation()
        p.strategy.upsert_object("fwd_2", "obstacle", {"x": 1, "y": 2}, 0.9, cycle=1)
        obj = p.get_object("fwd_2")
        assert obj is not None
        assert obj.id == "fwd_2"

    def test_get_objects_by_type_forwarded(self):
        p = StateEstimation()
        p.strategy.upsert_object("fwd_3", "waypoint", {"x": 10, "y": 10}, 1.0, cycle=1)
        results = p.get_objects_by_type("waypoint")
        assert len(results) == 1
        assert results[0].id == "fwd_3"

    def test_get_nonexistent_forwarded(self):
        p = StateEstimation()
        assert p.get_object("nonexistent") is None

    def test_update_environment_forwarded(self):
        p = StateEstimation()
        p.update_environment(terrain="mars")
        assert p.strategy.environment.terrain == "mars"

    def test_remove_stale_forwarded(self):
        p = StateEstimation()
        p.strategy.upsert_object("stale", "obstacle", {"x": 0, "y": 0}, 0.5, cycle=1)
        p.strategy.upsert_object("fresh", "obstacle", {"x": 1, "y": 1}, 0.9, cycle=10)
        removed = p.remove_stale_objects(current_cycle=10, max_age=5)
        assert removed == 1
        assert p.strategy.get_object("stale") is None
        assert p.strategy.get_object("fresh") is not None


class TestStateEstimationEdgeCases:
    def test_empty_strategy(self):
        p = StateEstimation()
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert result.metrics["obstacle_count"] == 0
        assert result.metrics["objects_tracked"] == 0

    def test_strategy_switch(self):
        p = StateEstimation()
        assert isinstance(p.strategy, SimpleObjectRegistry)
        p.strategy = SSKPM()
        assert isinstance(p.strategy, SSKPM)

    def test_physical_understanding_serializable(self):
        p = StateEstimation()
        p.strategy.upsert_object("ser_test", "obstacle", {"x": 1, "y": 2}, 0.9, cycle=1)
        understanding = p.physical_understanding
        assert "objects" in understanding
        assert understanding["obstacle_count"] == 1

    def test_lots_of_observations(self):
        p = StateEstimation()
        obs_list = [
            StateEstimationObservation(f"cam_{i}", f"obj_{i}", "obstacle",
                                 {"x": float(i), "y": float(i * 2)}, 0.8, 1)
            for i in range(50)
        ]
        p.ingest_observations(obs_list)
        state = RobotState()
        context = RuntimeContext()
        result = p.execute(state, context)
        assert result.metrics["observations_received"] == 50
        assert result.metrics["obstacle_count"] == 50

    def test_prediction_cache_accessible(self):
        p = StateEstimation()
        state = RobotState()
        context = RuntimeContext()
        p.execute(state, context)
        assert isinstance(p._prediction_cache, dict)
