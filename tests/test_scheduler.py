from cores.core import (
    RobotState,
    RuntimeContext,
    Scheduler,
    DefaultSchedulingPolicy,
    ExecutionPlan,
)
from cores.interfaces import Module, ModuleResult
from cores.events import Event, EventType


class StubModule(Module):
    """
    A concrete stub module for testing scheduler behavior.
    """

    async def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, success=True)


def test_default_scheduling_policy() -> None:
    """
    Verify that DefaultSchedulingPolicy schedules all modules in registered order.
    """
    policy = DefaultSchedulingPolicy()
    modules = [
        StubModule("sensor_processor"),
        StubModule("safety_monitor"),
        StubModule("navigator"),
    ]
    state = RobotState()
    context = RuntimeContext()
    events = []

    plan = policy.schedule(modules, state, context, events)

    assert isinstance(plan, ExecutionPlan)
    assert len(plan.modules) == 3
    assert plan.modules[0].name == "sensor_processor"
    assert plan.modules[1].name == "safety_monitor"
    assert plan.modules[2].name == "navigator"


def test_scheduler_delegation() -> None:
    """
    Verify that the Scheduler correctly delegates to the configured policy.
    """
    policy = DefaultSchedulingPolicy()
    scheduler = Scheduler(policy)
    modules = [StubModule("module_a")]
    state = RobotState()
    context = RuntimeContext()
    events = [Event(source="test", event_type=EventType.DIAGNOSTIC)]

    plan = scheduler.schedule(modules, state, context, events)

    assert isinstance(plan, ExecutionPlan)
    assert plan.modules == modules
    assert scheduler.policy == policy


def test_scheduler_determinism_and_purity() -> None:
    """
    Verify scheduler behaves as a pure function and executes deterministically.
    """
    scheduler = Scheduler(DefaultSchedulingPolicy())
    modules = [StubModule("m1"), StubModule("m2")]
    state = RobotState()
    context = RuntimeContext()
    events = [Event(source="t", event_type=EventType.STATE_UPDATED)]

    # Run twice
    plan_1 = scheduler.schedule(modules, state, context, events)
    plan_2 = scheduler.schedule(modules, state, context, events)

    # Outputs must be identical
    assert plan_1.modules == plan_2.modules

    # Inputs must not be mutated
    assert len(modules) == 2
    assert len(events) == 1
