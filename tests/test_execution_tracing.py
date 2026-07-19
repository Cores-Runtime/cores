from cores.core import ExecutionLayer, ExecutionPlan, TraceEntry
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.interfaces.module import Module, ModuleResult, ModuleStatus


class TraceMockModule(Module):
    def __init__(self, name: str, fail: bool = False) -> None:
        super().__init__(name)
        self.fail = fail

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        if self.fail:
            raise RuntimeError("module failure")
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS, execution_time_ms=1.5)


def test_execution_layer_trace_records_entries() -> None:
    layer = ExecutionLayer(tracing_enabled=True)
    plan = ExecutionPlan(modules=[TraceMockModule("m1"), TraceMockModule("m2")])
    context = RuntimeContext(cycle_count=5)
    results = layer.execute(plan, RobotState(), context)

    assert len(results) == 2
    trace = layer.execution_trace
    assert len(trace) == 2
    assert trace[0].module_name == "m1"
    assert trace[0].status == ModuleStatus.SUCCESS
    assert trace[0].cycle == 5
    assert trace[1].module_name == "m2"


def test_execution_layer_trace_failure_recorded() -> None:
    layer = ExecutionLayer(tracing_enabled=True)
    plan = ExecutionPlan(modules=[TraceMockModule("will_fail", fail=True)])
    context = RuntimeContext(cycle_count=0)
    results = layer.execute(plan, RobotState(), context)

    assert len(results) == 1
    assert results[0].status == ModuleStatus.FAILURE
    assert "module failure" in results[0].error_message

    trace = layer.execution_trace
    assert len(trace) == 1
    assert trace[0].module_name == "will_fail"
    assert trace[0].status == ModuleStatus.FAILURE


def test_execution_layer_trace_disabled() -> None:
    layer = ExecutionLayer(tracing_enabled=False)
    plan = ExecutionPlan(modules=[TraceMockModule("m1")])
    results = layer.execute(plan, RobotState(), RuntimeContext())

    assert len(results) == 1
    assert len(layer.execution_trace) == 0


def test_execution_layer_clear_trace() -> None:
    layer = ExecutionLayer(tracing_enabled=True)
    plan = ExecutionPlan(modules=[TraceMockModule("m1")])
    layer.execute(plan, RobotState(), RuntimeContext())

    assert len(layer.execution_trace) == 1
    layer.clear_trace()
    assert len(layer.execution_trace) == 0


def test_trace_entry_to_dict() -> None:
    entry = TraceEntry(
        module_name="test_mod",
        status=ModuleStatus.SUCCESS,
        execution_time_ms=2.5,
        error_message=None,
        cycle=3,
    )
    d = entry.to_dict()
    assert d["module_name"] == "test_mod"
    assert d["status"] == "SUCCESS"
    assert d["execution_time_ms"] == 2.5
    assert d["cycle"] == 3
