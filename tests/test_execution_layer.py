from cores.core import ExecutionLayer, ExecutionPlan, RobotState, RuntimeContext
from cores.interfaces import Module, ModuleResult, ModuleStatus
from cores.events import Event, EventType


class CountingModule(Module):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.call_count = 0

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        self.call_count += 1
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


class EventModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(
            module_name=self.name,
            status=ModuleStatus.SUCCESS,
            events=[
                Event(source=self.name, event_type=EventType.DIAGNOSTIC, payload={})
            ],
        )


def test_execution_layer_runs_modules_in_plan_order() -> None:
    layer = ExecutionLayer()
    module_a = CountingModule("a")
    module_b = CountingModule("b")
    plan = ExecutionPlan(modules=[module_a, module_b])
    state = RobotState()
    context = RuntimeContext()

    results = layer.execute(plan, state, context)

    assert module_a.call_count == 1
    assert module_b.call_count == 1
    assert results[0].module_name == "a"
    assert results[1].module_name == "b"


def test_execution_layer_empty_plan() -> None:
    layer = ExecutionLayer()
    plan = ExecutionPlan()

    results = layer.execute(plan, RobotState(), RuntimeContext())

    assert results == []


def test_execution_layer_returns_module_results() -> None:
    layer = ExecutionLayer()
    module = EventModule("emitter")
    plan = ExecutionPlan(modules=[module])

    results = layer.execute(plan, RobotState(), RuntimeContext())

    assert len(results) == 1
    assert results[0].status == ModuleStatus.SUCCESS
    assert len(results[0].events) == 1


def test_execution_layer_does_not_publish_events() -> None:
    """ExecutionLayer returns events; it does not dispatch them."""
    layer = ExecutionLayer()
    module = EventModule("emitter")
    plan = ExecutionPlan(modules=[module])

    results = layer.execute(plan, RobotState(), RuntimeContext())

    assert len(results[0].events) == 1
