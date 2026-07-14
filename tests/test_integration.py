from cores.core import (
    Runtime,
    Scheduler,
    SchedulingPolicy,
    ExecutionLayer,
    ExecutionPlan,
    RobotState,
    RuntimeContext,
)
from cores.interfaces import Module, ModuleResult, ModuleStatus
from cores.events import Event, EventType


class DummyModule(Module):
    """
    A simple dummy module that registers its execution and emits a specific event.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.execution_count = 0

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        self.execution_count += 1

        # Emit a diagnostic event
        emitted_event = Event(
            source=self.name,
            event_type=EventType.DIAGNOSTIC,
            payload={"step": context.cycle_count, "count": self.execution_count},
        )
        return ModuleResult(
            module_name=self.name,
            status=ModuleStatus.SUCCESS,
            events=[emitted_event],
        )



class EventRecordingPolicy(SchedulingPolicy):
    """
    A test policy that records the events passed to the schedule call.
    """

    def __init__(self) -> None:
        self.recorded_events = []

    def schedule(
        self,
        modules,
        state,
        context,
        events,
    ) -> ExecutionPlan:
        self.recorded_events.append(events.copy())
        return ExecutionPlan(modules=modules.copy())


def test_complete_runtime_integration_cycle() -> None:
    """
    Verify one complete, end-to-end deterministic runtime cycle.
    """
    # 1. Setup components
    policy = EventRecordingPolicy()
    scheduler = Scheduler(policy)
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer)

    # 2. Register DummyModule
    module = DummyModule("telemetry_module")
    runtime.register_module(module)

    # Pre-conditions
    assert runtime.context.cycle_count == 0
    assert module.execution_count == 0
    assert len(runtime._buffered_events) == 0

    # 3. Execute Step 1 (Cycle 0)
    runtime.step()

    # Post-conditions Cycle 0
    assert runtime.context.cycle_count == 1
    assert module.execution_count == 1

    # Events verification:
    # During step 1, the module executes and returns 1 event.
    # The ExecutionLayer publishes it to the event_bus.
    # The Runtime's listener receives it and adds it to _buffered_events.
    assert len(runtime._buffered_events) == 1
    buffered_event = runtime._buffered_events[0]
    assert buffered_event.source == "telemetry_module"
    assert buffered_event.event_type == EventType.DIAGNOSTIC
    assert buffered_event.payload == {"step": 0, "count": 1}

    # Policy received no events during cycle 0 scheduling
    assert len(policy.recorded_events) == 1
    assert policy.recorded_events[0] == []

    # 4. Execute Step 2 (Cycle 1)
    runtime.step()

    # Post-conditions Cycle 1
    assert runtime.context.cycle_count == 2
    assert module.execution_count == 2

    # During step 2, the buffered event from cycle 0 is harvested and passed to schedule()
    assert len(policy.recorded_events) == 2
    # The second schedule call should have received the event from cycle 0
    assert len(policy.recorded_events[1]) == 1
    received_event = policy.recorded_events[1][0]
    assert received_event == buffered_event

    # A new event is now buffered from the second execution
    assert len(runtime._buffered_events) == 1
    assert runtime._buffered_events[0].payload == {"step": 1, "count": 2}
