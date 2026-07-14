from unittest.mock import MagicMock
from cores.core import (
    Runtime,
    Scheduler,
    DefaultSchedulingPolicy,
    ExecutionLayer,
    ExecutionPlan,
)
from cores.events import Event, EventType
from cores.interfaces import Module, ModuleResult
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


class MockModule(Module):
    async def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, success=True)


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
    execution_layer.execute = MagicMock()

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
