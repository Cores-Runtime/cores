"""Tests for alternative WorldModel implementations: OccupancyGrid, Semantic, Probabilistic, DynamicTracking, SSKPM."""

import pytest
from cores.core import (
    WorldModel, SimpleObjectRegistry, OccupancyGrid, SemanticWorldModel,
    ProbabilisticWorldModel, DynamicTrackingWorldModel, SSKPM,
    Runtime, RuntimeContext, Scheduler, DefaultSchedulingPolicy,
    ExecutionLayer,
)
from cores.interfaces.module import Module, ModuleResult
from cores.core.robot_state import RobotState


ALL_IMPLS = [
    ("SimpleObjectRegistry", SimpleObjectRegistry),
    ("OccupancyGrid", OccupancyGrid),
    ("SemanticWorldModel", SemanticWorldModel),
    ("ProbabilisticWorldModel", ProbabilisticWorldModel),
    ("DynamicTrackingWorldModel", DynamicTrackingWorldModel),
    ("SSKPM", SSKPM),
]


class TestInterface:
    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_is_world_model(self, name, cls):
        wm = cls()
        assert isinstance(wm, WorldModel)

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_defaults(self, name, cls):
        wm = cls()
        assert wm.environment.terrain == "unknown"
        assert wm.environment.weather == "clear"
        assert wm.objects == []
        assert wm.obstacle_count == 0
        assert wm.has_sensor_degradation is False
        assert wm.last_update_cycle == 0

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_upsert_and_retrieve(self, name, cls):
        wm = cls()
        obj = wm.upsert_object(
            "test_001", "obstacle", {"x": 10, "y": 20}, 0.95, cycle=1
        )
        assert obj.id == "test_001"
        assert obj.object_type == "obstacle"
        assert obj.confidence == 0.95
        assert obj.last_seen_cycle == 1
        retrieved = wm.get_object("test_001")
        assert retrieved is not None
        assert retrieved.id == "test_001"

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_upsert_update(self, name, cls):
        wm = cls()
        wm.upsert_object("obj_1", "obstacle", {"x": 0, "y": 0}, 0.5, cycle=1)
        updated = wm.upsert_object("obj_1", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=3)
        assert updated.confidence > 0.5
        assert updated.last_seen_cycle == 3
        assert len(wm.objects) == 1
        # Probabilistic/Dynamic/SSKPM fuse measurements, so exact position may differ
        if name not in ("ProbabilisticWorldModel", "DynamicTrackingWorldModel", "SSKPM"):
            assert updated.position["x"] == 5
            assert updated.position["y"] == 5

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_upsert_with_properties(self, name, cls):
        wm = cls()
        obj = wm.upsert_object(
            "prop_001", "waypoint", {"x": 1, "y": 2}, 1.0, cycle=1,
            properties={"color": "red", "priority": "high"},
        )
        assert obj.properties["color"] == "red"
        assert obj.properties["priority"] == "high"

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_get_nonexistent(self, name, cls):
        wm = cls()
        assert wm.get_object("nonexistent") is None

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_get_objects_by_type(self, name, cls):
        wm = cls()
        wm.upsert_object("a", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        wm.upsert_object("b", "obstacle", {"x": 1, "y": 1}, 0.8, cycle=1)
        wm.upsert_object("c", "waypoint", {"x": 2, "y": 2}, 1.0, cycle=1)
        assert len(wm.get_objects_by_type("obstacle")) == 2
        assert len(wm.get_objects_by_type("waypoint")) == 1
        assert len(wm.get_objects_by_type("nonexistent")) == 0

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_remove_stale(self, name, cls):
        wm = cls()
        wm.upsert_object("fresh", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=10)
        wm.upsert_object("stale", "obstacle", {"x": 1, "y": 1}, 0.5, cycle=1)
        removed = wm.remove_stale_objects(current_cycle=10, max_age=5)
        assert removed == 1
        assert wm.get_object("fresh") is not None
        assert wm.get_object("stale") is None

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_remove_object(self, name, cls):
        wm = cls()
        wm.upsert_object("to_remove", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        assert wm.get_object("to_remove") is not None
        assert wm.remove_object("to_remove") is True
        assert wm.get_object("to_remove") is None
        assert wm.remove_object("to_remove") is False

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_update_environment(self, name, cls):
        wm = cls()
        wm.update_environment(terrain="rocky", weather="dust_storm", temperature=-10.0)
        assert wm.environment.terrain == "rocky"
        assert wm.environment.weather == "dust_storm"
        assert wm.environment.temperature == -10.0

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_obstacle_count(self, name, cls):
        wm = cls()
        assert wm.obstacle_count == 0
        wm.upsert_object("o1", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        assert wm.obstacle_count == 1
        wm.upsert_object("o2", "waypoint", {"x": 1, "y": 1}, 0.9, cycle=1)
        assert wm.obstacle_count == 1

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_sensor_degradation(self, name, cls):
        wm = cls()
        assert wm.has_sensor_degradation is False
        wm.uncertainty.sensor_health["lidar"] = 0.3
        assert wm.has_sensor_degradation is True
        wm.uncertainty.sensor_health["lidar"] = 0.8
        assert wm.has_sensor_degradation is False

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_predict_returns_dict(self, name, cls):
        wm = cls()
        result = wm.predict(steps=3)
        assert isinstance(result, dict)
        assert "method" in result

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_serialize_returns_dict(self, name, cls):
        wm = cls()
        wm.upsert_object("ser_001", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        data = wm.serialize()
        assert isinstance(data, dict)
        assert "type" in data
        assert "environment" in data
        assert "obstacle_count" in data

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_explain_returns_string(self, name, cls):
        wm = cls()
        explanation = wm.explain()
        assert isinstance(explanation, str)
        assert len(explanation) > 0

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_runtime_integration(self, name, cls):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer, world_model=cls())

        class WMTestModule(Module):
            def execute(self, state, context):
                context.world_model.upsert_object("r_001", "obstacle", {"x": 3, "y": 7}, 0.88, cycle=context.cycle_count)
                return ModuleResult(module_name=self.name)

        runtime.register_module(WMTestModule("wm_test"))
        runtime.step()
        assert runtime.world_model.obstacle_count == 1
        obj = runtime.world_model.get_object("r_001")
        assert obj is not None
        assert obj.confidence == 0.88


class TestOccupancyGrid:
    def test_cell_probability(self):
        og = OccupancyGrid()
        og.upsert_object("o1", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        prob = og.get_cell_probability(*og.world_to_grid(5, 5))
        assert prob > 0.5

    def test_query_occupancy(self):
        og = OccupancyGrid()
        og.upsert_object("o1", "obstacle", {"x": 10, "y": 10}, 0.9, cycle=1)
        assert og.query_occupancy(10, 10) > 0.5
        # Cell that has never been updated returns probability 0.5 (log-odds 0)
        # A value of exactly 0.5 means no information
        assert og.query_occupancy(-100, -100) == 0.5

    def test_region_query(self):
        og = OccupancyGrid()
        og.upsert_object("o1", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        og.upsert_object("o2", "obstacle", {"x": 15, "y": 15}, 0.8, cycle=1)
        region = og.get_objects_in_region(0, 0, 10, 10)
        assert len(region) == 1
        assert region[0].id == "o1"

    def test_export_cells(self):
        og = OccupancyGrid()
        og.upsert_object("o1", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        cells = og._export_cells()
        assert len(cells) >= 1

    def test_movement_updates_grid(self):
        og = OccupancyGrid()
        og.upsert_object("moving", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        og.upsert_object("moving", "obstacle", {"x": 15, "y": 15}, 0.9, cycle=2)
        p1 = og.query_occupancy(0, 0)
        p2 = og.query_occupancy(15, 15)
        assert p2 > p1


class TestSemanticWorldModel:
    def test_default_nodes(self):
        swm = SemanticWorldModel()
        assert swm.get_object("environment") is not None
        assert swm.get_object("robot") is not None

    def test_add_relation(self):
        swm = SemanticWorldModel()
        swm.upsert_object("rock_1", "obstacle", {"x": 5, "y": 5}, 0.9, cycle=1)
        swm.add_relation("rock_1", "environment", "located_in")
        relations = swm.query_relations("rock_1")
        assert any(r["relation"] == "located_in" for r in relations)

    def test_query_connected(self):
        swm = SemanticWorldModel()
        swm.upsert_object("a", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        swm.add_relation("a", "environment", "located_in")
        connected = swm.query_connected_nodes("a", "located_in")
        assert "environment" in connected

    def test_environment_update_syncs_node(self):
        swm = SemanticWorldModel()
        swm.update_environment(terrain="swamp")
        assert swm._nodes["environment"].properties["terrain"] == "swamp"


class TestProbabilisticWorldModel:
    def test_belief_tracking(self):
        pwm = ProbabilisticWorldModel()
        obj = pwm.upsert_object("obs_1", "obstacle", {"x": 10, "y": 20}, 0.7, cycle=1)
        assert obj.confidence == 0.7
        belief = pwm.get_belief("obs_1")
        assert belief is not None
        assert "x" in belief.position

    def test_confidence_increases_with_updates(self):
        pwm = ProbabilisticWorldModel()
        pwm.upsert_object("obs_1", "obstacle", {"x": 10, "y": 20}, 0.5, cycle=1)
        pwm.upsert_object("obs_1", "obstacle", {"x": 11, "y": 19}, 0.6, cycle=2)
        obj = pwm.get_object("obs_1")
        assert obj is not None
        assert obj.confidence > 0.5

    def test_prediction_decays_confidence(self):
        pwm = ProbabilisticWorldModel()
        pwm.upsert_object("obs_1", "obstacle", {"x": 10, "y": 20}, 0.9, cycle=5)
        pred = pwm.predict(steps=10)
        obj_pred = pred["predicted_objects"]["obs_1"]
        assert obj_pred["confidence"] < 0.9

    def test_uncertainty_query(self):
        pwm = ProbabilisticWorldModel()
        pwm.upsert_object("obs_1", "obstacle", {"x": 10, "y": 10}, 0.9, cycle=1)
        uncert = pwm.get_uncertainty_at(10, 10, radius=5)
        assert uncert >= 0


class TestDynamicTrackingWorldModel:
    def test_motion_tracking(self):
        dtm = DynamicTrackingWorldModel(dt=1.0)
        dtm.upsert_object("moving", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        dtm.upsert_object("moving", "obstacle", {"x": 5, "y": 0}, 0.9, cycle=2)
        motion = dtm.query_motion("moving")
        assert abs(motion["vx"]) > 0

    def test_prediction_with_velocity(self):
        dtm = DynamicTrackingWorldModel(dt=1.0)
        dtm.upsert_object("moving", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        dtm.upsert_object("moving", "obstacle", {"x": 5, "y": 0}, 0.9, cycle=2)
        pred = dtm.predict_position_at("moving", future_steps=1)
        assert pred is not None
        assert pred["x"] > 5

    def test_predict_many_objects(self):
        dtm = DynamicTrackingWorldModel()
        dtm.upsert_object("a", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=1)
        dtm.upsert_object("b", "obstacle", {"x": 10, "y": 10}, 0.8, cycle=1)
        pred = dtm.predict(steps=3)
        assert len(pred["predicted_objects"]) == 2

    def test_stale_removal(self):
        dtm = DynamicTrackingWorldModel()
        dtm.upsert_object("recent", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=10)
        dtm.upsert_object("old", "obstacle", {"x": 1, "y": 1}, 0.5, cycle=1)
        assert dtm.remove_stale_objects(current_cycle=10, max_age=5) == 1
        assert dtm.get_object("old") is None
        assert dtm.get_object("recent") is not None

    def test_get_track(self):
        dtm = DynamicTrackingWorldModel()
        dtm.upsert_object("t1", "obstacle", {"x": 1, "y": 2}, 0.9, cycle=1)
        track = dtm.get_track("t1")
        assert track is not None
        assert track.x == 1
        assert track.y == 2


class TestSSKPM:
    def test_kinematic_tracking(self):
        sskpm = SSKPM(dt=1.0)
        sskpm.upsert_object("obj", "obstacle", {"x": 0, "y": 0, "z": 0}, 0.9, cycle=1)
        sskpm.upsert_object("obj", "obstacle", {"x": 2, "y": 1, "z": 0}, 0.9, cycle=2)
        track = sskpm.get_track("obj")
        assert track is not None
        assert abs(track.vx) > 0 or abs(track.vy) > 0

    def test_prediction_with_acceleration(self):
        sskpm = SSKPM(dt=1.0)
        sskpm.upsert_object("obj", "obstacle", {"x": 0, "y": 0, "z": 0}, 0.9, cycle=1)
        sskpm.upsert_object("obj", "obstacle", {"x": 1, "y": 0, "z": 0}, 0.9, cycle=2)
        sskpm.upsert_object("obj", "obstacle", {"x": 3, "y": 0, "z": 0}, 0.9, cycle=3)
        pred = sskpm.predict(steps=2)
        assert "obj" in pred["predicted_objects"]
        assert pred["predicted_objects"]["obj"]["position"]["x"] > 3

    def test_region_query(self):
        sskpm = SSKPM()
        sskpm.upsert_object("near", "obstacle", {"x": 5, "y": 5, "z": 0}, 0.9, cycle=1)
        sskpm.upsert_object("far", "obstacle", {"x": 200, "y": 200, "z": 0}, 0.9, cycle=1)
        region = sskpm.query_region(0, 0, 50, 50)
        assert len(region) == 1
        assert region[0].id == "near"

    def test_nearest_query(self):
        sskpm = SSKPM()
        sskpm.upsert_object("close", "obstacle", {"x": 2, "y": 3, "z": 0}, 0.9, cycle=1)
        sskpm.upsert_object("far", "obstacle", {"x": 100, "y": 100, "z": 0}, 0.8, cycle=1)
        nearest = sskpm.query_nearest(0, 0, k=1)
        assert len(nearest) == 1
        assert nearest[0].id == "close"

    def test_stale_removal(self):
        sskpm = SSKPM()
        sskpm.upsert_object("fresh", "obstacle", {"x": 0, "y": 0, "z": 0}, 0.9, cycle=10)
        sskpm.upsert_object("stale", "obstacle", {"x": 1, "y": 1, "z": 0}, 0.5, cycle=1)
        assert sskpm.remove_stale_objects(current_cycle=10, max_age=5) == 1
        assert sskpm.get_object("stale") is None

    def test_chunk_movement(self):
        sskpm = SSKPM(chunk_size=10.0, dt=1.0)
        sskpm.upsert_object("mover", "obstacle", {"x": 0, "y": 0, "z": 0}, 0.9, cycle=1)
        sskpm.upsert_object("mover", "obstacle", {"x": 50, "y": 0, "z": 0}, 0.9, cycle=2)
        region = sskpm.query_region(40, -10, 60, 10)
        assert len(region) == 1
        obj = sskpm.get_object("mover")
        assert obj is not None
        # Kinematic filter smooths the jump; position should move toward 50
        assert obj.position["x"] > 40

    def test_explain_log(self):
        sskpm = SSKPM()
        sskpm.upsert_object("test", "obstacle", {"x": 1, "y": 2, "z": 0}, 0.9, cycle=1)
        sskpm.update_environment(terrain="lunar")
        explanation = sskpm.explain()
        assert "SSKPM" in explanation
        assert "test" in explanation or "obstacle" in explanation

    def test_clear_explain_log(self):
        sskpm = SSKPM()
        sskpm.upsert_object("test", "obstacle", {"x": 0, "y": 0, "z": 0}, 0.9, cycle=1)
        sskpm.clear_explain_log()
        # Should not crash
        assert sskpm.explain() is not None

    def test_3d_position(self):
        sskpm = SSKPM()
        obj = sskpm.upsert_object("drone", "agent", {"x": 10, "y": 20, "z": 30}, 0.95, cycle=1)
        assert obj.position["z"] == 30
        track = sskpm.get_track("drone")
        assert track.z == 30

    def test_obstacle_count_high_confidence_threshold(self):
        sskpm = SSKPM()
        sskpm.upsert_object("low_conf", "obstacle", {"x": 0, "y": 0, "z": 0}, 0.1, cycle=1)
        assert sskpm.obstacle_count == 0
        sskpm.upsert_object("high_conf", "obstacle", {"x": 1, "y": 1, "z": 0}, 0.8, cycle=1)
        assert sskpm.obstacle_count == 1


class TestRuntimeWithAllModels:
    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_runtime_accepts_world_model(self, name, cls):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        wm = cls()
        runtime = Runtime(scheduler, execution_layer, world_model=wm)
        assert runtime.world_model is wm

    @pytest.mark.parametrize("name,cls", ALL_IMPLS)
    def test_bridge_snapshot_serializable(self, name, cls):
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        runtime = Runtime(scheduler, execution_layer, world_model=cls())

        class Writer(Module):
            def execute(self, state, context):
                context.world_model.upsert_object("b", "obstacle", {"x": 1, "y": 2}, 0.9, cycle=context.cycle_count)
                context.world_model.update_environment(terrain="test")
                return ModuleResult(module_name=self.name)

        runtime.register_module(Writer("w"))
        runtime.step()
        snapshot = runtime.bridge.snapshot()
        assert snapshot is not None
        data = snapshot.model_dump()
        assert "world_model" in data


class TestIsolation:
    def test_independent_runtimes_independent_world_models(self):
        r1 = Runtime(Scheduler(DefaultSchedulingPolicy()), ExecutionLayer(), world_model=SSKPM())
        r2 = Runtime(Scheduler(DefaultSchedulingPolicy()), ExecutionLayer(), world_model=SSKPM())
        assert r1.world_model is not r2.world_model
        r1.world_model.update_environment(terrain="lava")
        assert r2.world_model.environment.terrain == "unknown"

    def test_different_impls_different_runtimes(self):
        r1 = Runtime(Scheduler(DefaultSchedulingPolicy()), ExecutionLayer(), world_model=SimpleObjectRegistry())
        r2 = Runtime(Scheduler(DefaultSchedulingPolicy()), ExecutionLayer(), world_model=OccupancyGrid())
        assert type(r1.world_model) is not type(r2.world_model)
