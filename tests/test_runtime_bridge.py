from unittest.mock import MagicMock
from cores.core import (
    Runtime,
    Scheduler,
    DefaultSchedulingPolicy,
    ExecutionLayer,
    ExecutionPlan,
    SimulatedStateEstimator,
)
from cores.events import Event, EventType
from cores.interfaces import Module, ModuleResult, ModuleStatus
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.runtime import (
    RuntimeState,
    RuntimeBridge,
    InMemoryRuntimeBridge,
    RuntimeStateBuilder,
    MissionState,
    SchedulerState,
    RobotSnapshot,
    EventsSnapshot,
    ExplainabilityState,
)


class MockModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


def test_runtime_bridge_default_attached_to_runtime() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    assert isinstance(runtime.bridge, InMemoryRuntimeBridge)


def test_runtime_bridge_custom_bridge() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    custom = InMemoryRuntimeBridge()
    runtime = Runtime(scheduler, execution_layer, bridge=custom)
    assert runtime.bridge is custom


def test_runtime_bridge_publishes_on_step() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(MockModule("m1"))
    runtime.register_module(MockModule("m2"))

    assert runtime.bridge.snapshot_count == 0
    runtime.step()
    assert runtime.bridge.snapshot_count == 1
    runtime.step()
    assert runtime.bridge.snapshot_count == 2


def test_runtime_bridge_snapshot_has_structure() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(MockModule("test_mod"))
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert snapshot is not None
    assert isinstance(snapshot.timestamp, str) or hasattr(snapshot.timestamp, "isoformat")
    assert isinstance(snapshot.mission, MissionState)
    assert isinstance(snapshot.scheduler, SchedulerState)
    assert isinstance(snapshot.robot, RobotSnapshot)
    assert isinstance(snapshot.events, EventsSnapshot)
    assert isinstance(snapshot.explainability, ExplainabilityState)
    assert len(snapshot.modules) == 1
    assert snapshot.modules[0].name == "test_mod"
    assert "test_mod" in snapshot.active_module_names


def test_runtime_bridge_snapshot_contains_scheduler_info() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(MockModule("m1"))
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert snapshot.scheduler.cycle_count == 1
    assert len(snapshot.modules) == 1
    assert snapshot.modules[0].name == "m1"
    assert "m1" in snapshot.active_module_names


def test_runtime_bridge_snapshot_robot_state() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    estimator = SimulatedStateEstimator()
    runtime = Runtime(scheduler, execution_layer, state_estimator=estimator)
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert snapshot.robot.battery_level == 1.0
    assert snapshot.robot.position.get("x") == 0.0


def test_runtime_bridge_snapshot_with_events() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(MockModule("m1"))

    event = Event(source="test", event_type=EventType.DIAGNOSTIC, payload={"v": 42})
    runtime.event_bus.publish(event)
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert len(snapshot.events.cycle_events) == 1
    assert snapshot.events.cycle_events[0]["source"] == "test"
    assert snapshot.events.cycle_events[0]["event_type"] == "diagnostic"


def test_runtime_bridge_snapshot_with_emergency_event() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(MockModule("m1"))

    event = Event(source="sensor", event_type=EventType.SYSTEM_EMERGENCY, payload={"code": 99})
    runtime.event_bus.publish(event)
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert len(snapshot.events.warnings) == 1


def test_collecting_bridge_records_all_snapshots() -> None:
    bridge = InMemoryRuntimeBridge()
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)

    runtime.register_module(MockModule("m1"))
    runtime.step()
    runtime.step()
    runtime.step()

    assert bridge.snapshot_count == 3
    assert len(bridge.snapshots) == 3
    for i, snap in enumerate(bridge.snapshots):
        assert snap.scheduler.cycle_count == i + 1


def test_collecting_bridge_subscribe() -> None:
    bridge = InMemoryRuntimeBridge()
    received = []

    def cb(state: RuntimeState) -> None:
        received.append(state)

    bridge.subscribe(cb)

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(MockModule("m1"))
    runtime.step()

    assert len(received) == 1
    assert received[0].scheduler.cycle_count == 1


def test_collecting_bridge_multiple_subscribers() -> None:
    bridge = InMemoryRuntimeBridge()
    r1, r2 = [], []

    bridge.subscribe(lambda s: r1.append(s))
    bridge.subscribe(lambda s: r2.append(s))

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(MockModule("m1"))
    runtime.step()

    assert len(r1) == 1
    assert len(r2) == 1


def test_collecting_bridge_close() -> None:
    bridge = InMemoryRuntimeBridge()
    bridge.subscribe(lambda s: None)

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(MockModule("m1"))
    runtime.step()

    assert bridge.snapshot() is not None

    bridge.close()
    assert bridge.snapshot() is None
    assert bridge.snapshot_count == 1


def test_runtime_bridge_without_events() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(MockModule("m1"))
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    assert snapshot.events.cycle_events == []
    assert snapshot.events.warnings == []
    assert snapshot.events.obstacles == []
    assert snapshot.events.recoveries == []


def test_runtime_builder_standalone() -> None:
    builder = RuntimeStateBuilder()
    state = RobotState(battery_level=0.75, mission_status="active", pose={"x": 5.0, "y": 3.0})
    context = RuntimeContext(cycle_count=4, scheduler_mode="default")
    context.metrics["policy"] = "default"
    context.metrics["selected"] = ["m1"]
    context.metrics["deferred"] = []

    module = MockModule("m1")

    result = builder.build(
        state=state,
        context=context,
        modules=[module],
        module_results=[],
        cycle_events=[],
        decision_time_ms=1.5,
    )

    assert result.scheduler.cycle_count == 4
    assert result.scheduler.policy == "default"
    assert result.scheduler.selected_modules == ["m1"]
    assert result.robot.battery_level == 0.75
    assert result.robot.position["x"] == 5.0
    assert result.mission.state == "active"
    assert result.scheduler.decision_time_ms == 1.5


def test_runtime_bridge_snapshot_contains_explainability() -> None:
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)
    runtime.register_module(MockModule("m1"))
    runtime.step()

    snapshot = runtime.bridge.snapshot()
    rationale = snapshot.explainability.scheduler_rationale
    assert "Mode:" in rationale
    assert "Cycle:" in rationale
    assert rationale != ""
