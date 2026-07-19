import pytest
from cores.core import (
    WorldModel, SimpleObjectRegistry, EnvironmentState, DetectedObject, UncertaintyState,
    Runtime, RuntimeContext, Scheduler, DefaultSchedulingPolicy,
    ExecutionLayer,
)
from cores.interfaces.module import Module, ModuleResult, ModuleProfile
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.runtime import RuntimeState, WorldModelSnapshot


class WorldWritingModule(Module):
    def __init__(self, name: str, updates: dict | None = None) -> None:
        super().__init__(name)
        self.updates = updates or {}

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        wm = context.world_model
        for key, value in self.updates.items():
            if key == "terrain":
                wm.environment.terrain = value
            elif key == "weather":
                wm.environment.weather = value
            elif key == "obstacle":
                wm.upsert_object(
                    object_id=value["id"],
                    object_type=value.get("type", "obstacle"),
                    position=value.get("position", {"x": 0, "y": 0}),
                    confidence=value.get("confidence", 1.0),
                    cycle=context.cycle_count,
                )
            elif key == "sensor_health":
                wm.uncertainty.sensor_health.update(value)
        return ModuleResult(module_name=self.name)


class WorldReadingModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        wm = context.world_model
        return ModuleResult(
            module_name=self.name,
            metrics={
                "obstacle_count": wm.obstacle_count,
                "terrain": wm.environment.terrain,
                "weather": wm.environment.weather,
            },
        )


def test_world_model_defaults() -> None:
    wm = SimpleObjectRegistry()
    assert wm.environment.terrain == "unknown"
    assert wm.environment.weather == "clear"
    assert wm.environment.temperature == 20.0
    assert wm.environment.lighting == "day"
    assert wm.environment.hazards == []
    assert wm.environment.obstacle_distance == 10.0
    assert wm.objects == []
    assert wm.uncertainty.localization == 0.0
    assert wm.uncertainty.mapping == 0.0
    assert wm.uncertainty.perception == 0.0
    assert wm.uncertainty.sensor_health == {}
    assert wm.last_update_cycle == 0


def test_world_model_update_environment() -> None:
    wm = SimpleObjectRegistry()
    wm.update_environment(terrain="rocky", weather="dust_storm", temperature=-10.0)
    assert wm.environment.terrain == "rocky"
    assert wm.environment.weather == "dust_storm"
    assert wm.environment.temperature == -10.0
    assert wm.last_update_cycle > 0


def test_world_model_upsert_object_new() -> None:
    wm = SimpleObjectRegistry()
    obj = wm.upsert_object(
        object_id="rock_001",
        object_type="obstacle",
        position={"x": 5.0, "y": 3.0},
        confidence=0.95,
        cycle=1,
    )
    assert obj.id == "rock_001"
    assert obj.object_type == "obstacle"
    assert obj.position == {"x": 5.0, "y": 3.0}
    assert obj.confidence == 0.95
    assert obj.last_seen_cycle == 1
    assert len(wm.objects) == 1
    assert wm.obstacle_count == 1


def test_world_model_upsert_object_existing() -> None:
    wm = SimpleObjectRegistry()
    wm.upsert_object("rock_001", "obstacle", {"x": 5.0, "y": 3.0}, 0.95, cycle=1)
    updated = wm.upsert_object("rock_001", "obstacle", {"x": 6.0, "y": 4.0}, 0.98, cycle=5)
    assert updated.id == "rock_001"
    assert updated.position == {"x": 6.0, "y": 4.0}
    assert updated.confidence == 0.98
    assert updated.last_seen_cycle == 5
    assert len(wm.objects) == 1


def test_world_model_get_object() -> None:
    wm = SimpleObjectRegistry()
    wm.upsert_object("rock_001", "obstacle", {"x": 5.0, "y": 3.0}, 0.95, cycle=1)
    obj = wm.get_object("rock_001")
    assert obj is not None
    assert obj.id == "rock_001"
    assert wm.get_object("nonexistent") is None


def test_world_model_get_objects_by_type() -> None:
    wm = SimpleObjectRegistry()
    wm.upsert_object("rock_001", "obstacle", {"x": 1, "y": 1}, 0.9, cycle=1)
    wm.upsert_object("rock_002", "obstacle", {"x": 2, "y": 2}, 0.8, cycle=1)
    wm.upsert_object("area_51", "waypoint", {"x": 10, "y": 10}, 1.0, cycle=1)
    obstacles = wm.get_objects_by_type("obstacle")
    assert len(obstacles) == 2
    waypoints = wm.get_objects_by_type("waypoint")
    assert len(waypoints) == 1


def test_world_model_remove_stale_objects() -> None:
    wm = SimpleObjectRegistry()
    wm.upsert_object("fresh", "obstacle", {"x": 0, "y": 0}, 0.9, cycle=10)
    wm.upsert_object("stale", "obstacle", {"x": 1, "y": 1}, 0.5, cycle=1)
    removed = wm.remove_stale_objects(current_cycle=10, max_age=5)
    assert removed == 1
    assert wm.get_object("fresh") is not None
    assert wm.get_object("stale") is None


def test_world_model_uncertainty() -> None:
    wm = SimpleObjectRegistry()
    assert wm.has_sensor_degradation is False
    wm.uncertainty.sensor_health["lidar"] = 0.3
    assert wm.has_sensor_degradation is True
    wm.uncertainty.sensor_health["lidar"] = 0.8
    assert wm.has_sensor_degradation is False


def test_world_model_uncertainty_ranges() -> None:
    wm = SimpleObjectRegistry()
    wm.uncertainty.localization = 0.5
    wm.uncertainty.mapping = 0.3
    wm.uncertainty.perception = 0.8
    assert wm.uncertainty.localization == 0.5
    assert wm.uncertainty.mapping == 0.3
    assert wm.uncertainty.perception == 0.8


def test_world_model_accessible_via_context() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    assert runtime.world_model is not None
    assert isinstance(runtime.world_model, WorldModel)
    assert runtime.world_model.environment.terrain == "unknown"


def test_world_model_wired_into_context_before_step() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    writer = WorldWritingModule("writer", updates={"terrain": "mars_crater"})
    runtime.register_module(writer)

    assert runtime.context.world_model is None
    runtime.step()
    assert runtime.context.world_model is runtime.world_model
    assert runtime.world_model.environment.terrain == "mars_crater"


def test_world_model_module_writes_and_persists() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    writer = WorldWritingModule("writer", updates={
        "obstacle": {"id": "boulder", "type": "obstacle", "position": {"x": 12, "y": 5}, "confidence": 0.9},
        "sensor_health": {"camera": 0.4, "lidar": 0.9},
    })
    runtime.register_module(writer)
    runtime.step()

    wm = runtime.world_model
    assert wm.obstacle_count == 1
    assert wm.get_object("boulder") is not None
    assert wm.uncertainty.sensor_health["camera"] == 0.4
    assert wm.uncertainty.sensor_health["lidar"] == 0.9


def test_world_model_persists_across_cycles() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    runtime.register_module(WorldWritingModule("step1", updates={
        "obstacle": {"id": "rock_a", "type": "obstacle", "position": {"x": 1, "y": 1}, "confidence": 0.8},
    }))
    runtime.step()
    runtime.step()
    runtime.step()

    wm = runtime.world_model
    assert wm.obstacle_count == 1
    assert wm.get_object("rock_a") is not None
    assert wm.last_update_cycle == 2


def test_world_model_module_reads_via_context() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    writer = WorldWritingModule("writer", updates={"terrain": "volcanic"})
    reader = WorldReadingModule("reader")
    runtime.register_module(writer)
    runtime.register_module(reader)
    runtime.step()

    assert runtime.world_model.environment.terrain == "volcanic"


def test_world_model_bridge_snapshot_includes_world() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    runtime.register_module(WorldWritingModule("writer", updates={
        "terrain": "icy",
        "weather": "blizzard",
        "obstacle": {"id": "ice_001", "type": "obstacle", "position": {"x": 3, "y": 7}, "confidence": 0.85},
    }))
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert snapshot is not None
    assert isinstance(snapshot.world_model, WorldModelSnapshot)
    assert snapshot.world_model.environment.terrain == "icy"
    assert snapshot.world_model.environment.weather == "blizzard"
    assert snapshot.world_model.obstacle_count == 1
    assert len(snapshot.world_model.objects) == 1
    assert snapshot.world_model.objects[0].id == "ice_001"
    assert snapshot.world_model.objects[0].confidence == 0.85


def test_world_model_bridge_snapshot_empty() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(WorldWritingModule("noop"))
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert snapshot is not None
    assert snapshot.world_model.environment.terrain == "unknown"
    assert snapshot.world_model.obstacle_count == 0
    assert snapshot.world_model.objects == []


def test_world_model_multiple_objects() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    writer = WorldWritingModule("writer", updates={
        "obstacle": {"id": "rock_1", "type": "obstacle", "position": {"x": 1, "y": 1}, "confidence": 0.9},
    })
    runtime.register_module(writer)
    runtime.step()

    writer2 = WorldWritingModule("writer2", updates={
        "obstacle": {"id": "rock_2", "type": "obstacle", "position": {"x": 2, "y": 2}, "confidence": 0.8},
    })
    runtime.register_module(writer2)
    runtime.step()

    assert runtime.world_model.obstacle_count == 2
    assert runtime.world_model.get_object("rock_1") is not None
    assert runtime.world_model.get_object("rock_2") is not None


def test_world_model_upsert_with_properties() -> None:
    wm = SimpleObjectRegistry()
    obj = wm.upsert_object(
        object_id="sensor_01",
        object_type="waypoint",
        position={"x": 100, "y": 200},
        confidence=1.0,
        cycle=5,
        properties={"color": "red", "priority": "high"},
    )
    assert obj.properties["color"] == "red"
    assert obj.properties["priority"] == "high"


def test_world_model_update_environment_only_known_keys() -> None:
    wm = SimpleObjectRegistry()
    wm.update_environment(terrain="sand", unknown_field="should_be_ignored")
    assert wm.environment.terrain == "sand"
    assert not hasattr(wm.environment, "unknown_field")


def test_world_model_not_shared_across_independent_runtimes() -> None:
    r1 = Runtime(Scheduler(DefaultSchedulingPolicy()), ExecutionLayer())
    r2 = Runtime(Scheduler(DefaultSchedulingPolicy()), ExecutionLayer())
    assert r1.world_model is not r2.world_model
    r1.world_model.environment.terrain = "lava"
    assert r2.world_model.environment.terrain == "unknown"


def test_world_model_runtime_state_serializable() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    runtime.register_module(WorldWritingModule("w", updates={
        "terrain": "cave",
        "obstacle": {"id": "stalactite", "type": "obstacle", "position": {"x": 0, "y": 0}, "confidence": 0.99},
    }))
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    as_dict = snapshot.model_dump()
    assert "world_model" in as_dict
    assert as_dict["world_model"]["environment"]["terrain"] == "cave"
    assert as_dict["world_model"]["obstacle_count"] == 1
    assert len(as_dict["world_model"]["objects"]) == 1
    assert as_dict["world_model"]["objects"][0]["id"] == "stalactite"
