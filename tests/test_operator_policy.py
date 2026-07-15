from cores.core import (
    OperatorSchedulingPolicy,
    RobotState,
    RuntimeContext,
    ExecutionPlan,
)
from cores.interfaces import Module, ModuleResult, ModuleStatus


class PriorityModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


def test_operator_policy_orders_by_priority_descending() -> None:
    policy = OperatorSchedulingPolicy()
    modules = [
        PriorityModule("telemetry", priority=1),
        PriorityModule("safety_monitor", priority=10),
        PriorityModule("navigator", priority=5),
    ]

    plan = policy.schedule(modules, RobotState(), RuntimeContext(), [])

    assert isinstance(plan, ExecutionPlan)
    assert [m.name for m in plan.modules] == [
        "safety_monitor",
        "navigator",
        "telemetry",
    ]


def test_operator_policy_stable_order_for_equal_priority() -> None:
    policy = OperatorSchedulingPolicy()
    modules = [
        PriorityModule("first", priority=5),
        PriorityModule("second", priority=5),
        PriorityModule("third", priority=5),
    ]

    plan = policy.schedule(modules, RobotState(), RuntimeContext(), [])

    assert [m.name for m in plan.modules] == ["first", "second", "third"]


def test_operator_policy_deterministic() -> None:
    policy = OperatorSchedulingPolicy()
    modules = [
        PriorityModule("a", priority=3),
        PriorityModule("b", priority=7),
        PriorityModule("c", priority=1),
    ]
    state = RobotState()
    context = RuntimeContext()

    plan_1 = policy.schedule(modules, state, context, [])
    plan_2 = policy.schedule(modules, state, context, [])

    assert [m.name for m in plan_1.modules] == [m.name for m in plan_2.modules]


def test_operator_policy_does_not_mutate_input() -> None:
    policy = OperatorSchedulingPolicy()
    modules = [
        PriorityModule("low", priority=1),
        PriorityModule("high", priority=10),
    ]
    original_order = [m.name for m in modules]

    policy.schedule(modules, RobotState(), RuntimeContext(), [])

    assert [m.name for m in modules] == original_order


def test_operator_policy_schedules_all_modules() -> None:
    policy = OperatorSchedulingPolicy()
    modules = [PriorityModule(f"m{i}", priority=i) for i in range(4)]

    plan = policy.schedule(modules, RobotState(), RuntimeContext(), [])

    assert len(plan.modules) == 4
