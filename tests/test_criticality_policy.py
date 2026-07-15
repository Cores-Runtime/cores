from cores.core import (
    CriticalitySchedulingPolicy,
    CriticalityWeights,
    DefaultCriticalityScoringStrategy,
    ExecutionPlan,
    ResourcePenaltyWeights,
    RobotState,
    RuntimeContext,
)
from cores.events import Event, EventType
from cores.interfaces import Module, ModuleProfile, ModuleResult, ModuleStatus


class CriticalityModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


def _build_modules() -> list[Module]:
    return [
        CriticalityModule(
            "safety_monitor",
            priority=100,
            profile=ModuleProfile(
                safety_weight=0.9,
                urgency_weight=0.8,
                compute_cost=0.1,
                time_cost_ms=8.0,
                energy_cost=0.05,
                is_safety_critical=True,
            ),
        ),
        CriticalityModule(
            "diagnostics",
            priority=60,
            profile=ModuleProfile(
                safety_weight=0.7,
                urgency_weight=0.7,
                compute_cost=0.1,
                time_cost_ms=7.0,
                energy_cost=0.04,
                is_diagnostic=True,
            ),
        ),
        CriticalityModule(
            "localization",
            priority=50,
            profile=ModuleProfile(
                mission_weight=0.8,
                urgency_weight=0.6,
                compute_cost=0.2,
                time_cost_ms=12.0,
                energy_cost=0.08,
                mission_tags=frozenset({"explore"}),
                is_localization=True,
            ),
        ),
        CriticalityModule(
            "mapper",
            priority=40,
            profile=ModuleProfile(
                mission_weight=0.9,
                compute_cost=0.35,
                time_cost_ms=28.0,
                energy_cost=0.18,
                mission_tags=frozenset({"explore"}),
            ),
        ),
        CriticalityModule(
            "explorer",
            priority=30,
            profile=ModuleProfile(
                mission_weight=1.0,
                compute_cost=0.45,
                time_cost_ms=35.0,
                energy_cost=0.25,
                mission_tags=frozenset({"explore"}),
            ),
        ),
    ]


def test_criticality_policy_defer_high_energy_module_on_low_battery() -> None:
    policy = CriticalitySchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.05, mission_status="explore")
    context = RuntimeContext(compute_budget=1.0, time_budget_ms=100.0)

    plan = policy.schedule(modules, state, context, [])

    assert isinstance(plan, ExecutionPlan)
    assert "safety_monitor" in [module.name for module in plan.modules]
    assert "explorer" not in [module.name for module in plan.modules]
    assert context.scheduler_mode == "low_power"


def test_criticality_policy_prioritizes_diagnostics_and_localization_on_sensor_failure() -> None:
    policy = CriticalitySchedulingPolicy()
    modules = _build_modules()
    state = RobotState(
        battery_level=0.6,
        mission_status="explore",
        sensor_summaries={"gps": "offline", "camera": "degraded"},
        flags={"sensor_failure": True, "hardware_fault": True},
    )
    context = RuntimeContext(compute_budget=0.5, time_budget_ms=30.0)
    events = [Event(source="gps", event_type=EventType.MODULE_FAILED)]

    plan = policy.schedule(modules, state, context, events)
    selected_names = [module.name for module in plan.modules]

    assert selected_names[0] == "diagnostics"
    assert "safety_monitor" in selected_names
    assert "localization" in selected_names
    assert "mapper" not in selected_names


def test_criticality_policy_is_deterministic() -> None:
    policy = CriticalitySchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.6, mission_status="explore")
    context_one = RuntimeContext(compute_budget=0.6, time_budget_ms=40.0)
    context_two = RuntimeContext(compute_budget=0.6, time_budget_ms=40.0)
    events = [Event(source="sensor", event_type=EventType.DIAGNOSTIC)]

    plan_one = policy.schedule(modules, state, context_one, events)
    plan_two = policy.schedule(modules, state, context_two, events)

    assert [module.name for module in plan_one.modules] == [
        module.name for module in plan_two.modules
    ]
    assert context_one.metrics["scores"] == context_two.metrics["scores"]
    assert context_one.metrics["selected"] == context_two.metrics["selected"]


def test_scoring_strategy_uses_configurable_weights() -> None:
    module = CriticalityModule(
        "mapper",
        profile=ModuleProfile(
            mission_weight=1.0,
            compute_cost=0.1,
            time_cost_ms=10.0,
            energy_cost=0.1,
            mission_tags=frozenset({"explore"}),
        ),
    )
    state = RobotState(battery_level=1.0, mission_status="explore")
    context = RuntimeContext(compute_budget=1.0, time_budget_ms=100.0)

    baseline = DefaultCriticalityScoringStrategy().score(module, state, context, [])
    boosted = DefaultCriticalityScoringStrategy(
        weights=CriticalityWeights(mission=0.8, safety=0.1, urgency=0.05, resource_penalty=0.05),
        resource_weights=ResourcePenaltyWeights(compute=0.5, time=0.3, energy=0.2),
    ).score(module, state, context, [])

    assert boosted.value > baseline.value
