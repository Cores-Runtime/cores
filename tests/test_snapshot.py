import pytest
from cores.core.robot_state import RobotState
from cores.core.world_model.simple_registry import SimpleObjectRegistry
from cores.core.planning.snapshot import (
    PlanningSnapshotPolicy,
    build_planning_snapshot,
    diff_snapshots,
)


def _registry_with_objects(reverse: bool = False) -> SimpleObjectRegistry:
    reg = SimpleObjectRegistry()
    objects = [
        ("door_a", "obstacle", {"x": 1.0, "y": 2.0}, {"label": "main"}),
        ("door_b", "obstacle", {"x": 3.0, "y": 4.0}, {"label": "side"}),
    ]
    if reverse:
        objects = list(reversed(objects))
    for oid, otype, pos, props in objects:
        reg.upsert_object(
            object_id=oid,
            object_type=otype,
            position=pos,
            confidence=0.9,
            cycle=5,
            properties=props,
        )
    return reg


class TestPlanningSnapshotDeterminism:
    def test_same_inputs_same_output(self):
        reg = _registry_with_objects()
        state = RobotState(battery_level=0.7)
        s1 = build_planning_snapshot(state, reg)
        s2 = build_planning_snapshot(state, reg)
        assert s1 == s2

    def test_order_independent_objects(self):
        s1 = build_planning_snapshot(RobotState(), _registry_with_objects())
        s2 = build_planning_snapshot(RobotState(), _registry_with_objects(reverse=True))
        assert s1 == s2
        ids = [o["id"] for o in s1["objects"]]
        assert ids == sorted(ids)

    def test_flags_sorted_and_filtered(self):
        state = RobotState(
            flags={
                "navigation_fault": True,
                "sensor_fault": True,
                "ignored_flag": True,
                "payload_fault": False,
            }
        )
        snapshot = build_planning_snapshot(state, SimpleObjectRegistry())
        assert snapshot["fault_flags"] == ["navigation_fault", "sensor_fault"]

    def test_payload_sorted(self):
        state = RobotState(metadata={"payload": ["b", "a", "c"]})
        snapshot = build_planning_snapshot(state, SimpleObjectRegistry())
        assert snapshot["payload"] == ["a", "b", "c"]

    def test_no_raw_continuous_values(self):
        state = RobotState(battery_level=0.6123)
        snapshot = build_planning_snapshot(state, SimpleObjectRegistry())
        assert snapshot["battery_bucket"] == "high"
        assert "battery_level" not in snapshot

    def test_object_projection_excludes_jitter(self):
        reg = _registry_with_objects()
        snapshot = build_planning_snapshot(RobotState(), reg)
        obj = snapshot["objects"][0]
        assert set(obj) == {"id", "object_type", "position", "properties"}
        assert "confidence" not in obj
        assert "last_seen_cycle" not in obj

    def test_battery_buckets(self):
        policy = PlanningSnapshotPolicy()
        assert policy.battery_bucket(1.0) == "high"
        assert policy.battery_bucket(0.6) == "high"
        assert policy.battery_bucket(0.35) == "medium"
        assert policy.battery_bucket(0.15) == "low"
        assert policy.battery_bucket(0.05) == "critical"
        assert policy.battery_bucket(0.0) == "critical"

    def test_sensor_status_numeric_and_string(self):
        policy = PlanningSnapshotPolicy()
        assert policy.sensor_status(0.9) == "healthy"
        assert policy.sensor_status(0.3) == "degraded"
        assert policy.sensor_status(0.05) == "failed"
        assert policy.sensor_status("nominal") == "healthy"
        assert policy.sensor_status("unknown_status") == "unknown_status"

    def test_sensor_health_sorted(self):
        state = RobotState(sensor_summaries={"lidar": 0.9, "camera": 0.2})
        snapshot = build_planning_snapshot(state, SimpleObjectRegistry())
        assert list(snapshot["sensor_health"]) == ["camera", "lidar"]
        assert snapshot["sensor_health"]["camera"] == "degraded"
        assert snapshot["sensor_health"]["lidar"] == "healthy"

    def test_policy_is_frozen(self):
        policy = PlanningSnapshotPolicy()
        with pytest.raises((AttributeError, TypeError)):
            policy.battery_buckets = ((0.5, "half"),)

    def test_region_waypoint_default_none(self):
        snapshot = build_planning_snapshot(RobotState(), SimpleObjectRegistry())
        assert snapshot["region"] is None
        assert snapshot["waypoint"] is None

    def test_region_waypoint_passthrough(self):
        state = RobotState(metadata={"region": "zone_a", "waypoint": "wp3"})
        snapshot = build_planning_snapshot(state, SimpleObjectRegistry())
        assert snapshot["region"] == "zone_a"
        assert snapshot["waypoint"] == "wp3"

    def test_environment_projection(self):
        reg = SimpleObjectRegistry()
        reg.update_environment(terrain="rough", weather="rain", temperature=21.7)
        snapshot = build_planning_snapshot(RobotState(), reg)
        env = snapshot["environment"]
        assert env["terrain"] == "rough"
        assert env["weather"] == "rain"
        assert env["temperature"] == 22.0  # temperature_round_dp = 0
        assert env["obstacle_distance"] == 10.0


class TestDiffSnapshots:
    def test_no_change(self):
        reg = _registry_with_objects()
        s1 = build_planning_snapshot(RobotState(), reg)
        s2 = build_planning_snapshot(RobotState(), reg)
        assert diff_snapshots(s1, s2) == {}

    def test_object_change_detected(self):
        reg = SimpleObjectRegistry()
        s1 = build_planning_snapshot(RobotState(), reg)
        reg.upsert_object(
            object_id="door_a", object_type="obstacle",
            position={"x": 1.0, "y": 2.0}, confidence=0.9, cycle=1,
        )
        s2 = build_planning_snapshot(RobotState(), reg)
        changes = diff_snapshots(s1, s2)
        assert "objects" in changes

    def test_battery_bucket_change_detected(self):
        s1 = build_planning_snapshot(RobotState(battery_level=0.7), SimpleObjectRegistry())
        s2 = build_planning_snapshot(RobotState(battery_level=0.2), SimpleObjectRegistry())
        changes = diff_snapshots(s1, s2)
        assert changes["battery_bucket"] == {"from": "high", "to": "low"}

    def test_keys_sorted(self):
        s1 = build_planning_snapshot(
            RobotState(battery_level=0.7, flags={"sensor_fault": True}),
            SimpleObjectRegistry(),
        )
        s2 = build_planning_snapshot(
            RobotState(battery_level=0.2, flags={"navigation_fault": True}),
            SimpleObjectRegistry(),
        )
        changes = diff_snapshots(s1, s2)
        assert list(changes) == sorted(changes)

    def test_battery_drain_within_bucket_is_not_a_change(self):
        s1 = build_planning_snapshot(RobotState(battery_level=0.71), SimpleObjectRegistry())
        s2 = build_planning_snapshot(RobotState(battery_level=0.62), SimpleObjectRegistry())
        assert diff_snapshots(s1, s2) == {}
