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


class MockModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)



def test_runtime_initialization() -> None:
    """
    Verify that Runtime initializes its core components correctly.
    """
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    assert isinstance(runtime.state, RobotState)
    assert isinstance(runtime.context, RuntimeContext)
    assert runtime.context.cycle_count == 0
    assert runtime.scheduler == scheduler
    assert runtime.execution_layer == execution_layer
    assert len(runtime.modules) == 0


def test_runtime_module_registration() -> None:
    """
    Verify that modules can be registered without duplicates.
    """
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    module = MockModule("test_module")
    runtime.register_module(module)
    assert len(runtime.modules) == 1
    assert runtime.modules[0] == module

    # Try registering again
    runtime.register_module(module)
    assert len(runtime.modules) == 1


def test_runtime_cycle_execution() -> None:
    """
    Verify that a single step runs completely and increments cycle count.
    """
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()

    # Mock scheduler
    scheduler.schedule = MagicMock(return_value=ExecutionPlan())
    # Mock execution layer
    execution_layer.execute = MagicMock(return_value=[])

    runtime = Runtime(scheduler, execution_layer)
    module = MockModule("m1")
    runtime.register_module(module)

    assert runtime.context.cycle_count == 0
    runtime.step()

    # Verify cycle count advanced
    assert runtime.context.cycle_count == 1

    # Verify delegation calls
    scheduler.schedule.assert_called_once_with(
        runtime.modules, runtime.state, runtime.context, []
    )
    execution_layer.execute.assert_called_once()


def test_runtime_event_harvesting() -> None:
    """
    Verify that events emitted on the EventBus are harvested and passed to the scheduler in the next cycle.
    """
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    scheduler.schedule = MagicMock(return_value=ExecutionPlan())

    runtime = Runtime(scheduler, execution_layer)

    # Publish an event to the runtime's event bus
    event = Event(source="sensor", event_type=EventType.DIAGNOSTIC, payload={"v": 10})
    runtime.event_bus.publish(event)

    # Event should be buffered
    assert len(runtime._buffered_events) == 1
    assert runtime._buffered_events[0] == event

    # Execute step
    runtime.step()

    # The buffer should be cleared
    assert len(runtime._buffered_events) == 0

    # The scheduler should have received the event in its parameters
    scheduler.schedule.assert_called_once_with(
        runtime.modules, runtime.state, runtime.context, [event]
    )


def test_runtime_state_estimator_updates_state() -> None:
    """
    Verify that a configured StateEstimator updates RobotState at the start of each cycle.
    """
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    estimator = SimulatedStateEstimator()
    runtime = Runtime(scheduler, execution_layer, state_estimator=estimator)

    assert runtime.state.battery_level == 1.0
    assert runtime.state.pose == {}

    runtime.step()

    assert runtime.state.battery_level == 1.0
    assert runtime.state.pose["x"] == 0.0
    assert runtime.state.metadata["source"] == "simulated"

    runtime.step()

    assert runtime.state.battery_level == 0.99
    assert runtime.state.pose["x"] == 0.1


def test_runtime_wires_default_memory_logger() -> None:
    """
    Verify Runtime constructs a Memory with a Logger by default.
    """
    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    assert runtime.memory.logger is not None
    assert runtime.memory.episodic is not None
    assert runtime.memory.semantic is not None


def test_runtime_logger_consolidates_outcomes() -> None:
    """
    Verify the Episodic -> Logger -> Semantic pipeline runs during Runtime.step().
    """
    from cores.core import (
        Memory,
        MemoryRecord,
        MemoryType,
        EpisodicStore,
        FIFOMemoryStrategy,
        Logger,
        SPSCALogger,
        CountTrigger,
    )

    memory = Memory(
        episodic_store=EpisodicStore(FIFOMemoryStrategy(max_size=100)),
        logger=Logger(strategy=SPSCALogger(), trigger=CountTrigger(count=3)),
        archive_below=0.6,
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, memory=memory)

    for cycle in range(4):
        runtime.memory.store(MemoryRecord(
            id=f"outcome_{cycle}",
            content={"action": "OpenDoor", "result": "Failed"},
            cycle=cycle,
            importance=0.4,
            record_type=MemoryType.OUTCOME,
        ))
        runtime.step()

    assert runtime.memory.semantic.narrative_count > 0

    narratives = runtime.memory.semantic.query_narratives()
    assert narratives[0].compression is not None
    assert len(narratives[0].compression.source_ids) > 0

