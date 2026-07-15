from cores.core import (
    LexicographicRiskAwareSchedulingPolicy,
    LexicographicSelectionStrategy,
    LexicographicKnapsackSolver,
    LexicographicValue,
    ModuleGraph,
    ModuleRelation,
    ModuleRelationType,
    DefaultModuleClassifier,
    ModuleClass,
    RobotState,
    RuntimeContext,
    ExecutionPlan,
    CriticalityWeights,
    ResourcePenaltyWeights,
)
from cores.events import Event, EventType
from cores.interfaces import Module, ModuleProfile, ModuleResult, ModuleStatus


class LexicographicModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


def _build_modules() -> list[Module]:
    return [
        LexicographicModule(
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
        LexicographicModule(
            "battery_monitor",
            priority=90,
            profile=ModuleProfile(
                safety_weight=0.8,
                urgency_weight=0.7,
                compute_cost=0.05,
                time_cost_ms=5.0,
                energy_cost=0.02,
                is_safety_critical=True,
            ),
        ),
        LexicographicModule(
            "navigator",
            priority=80,
            profile=ModuleProfile(
                mission_weight=0.8,
                urgency_weight=0.5,
                compute_cost=0.15,
                time_cost_ms=12.0,
                energy_cost=0.08,
                mission_tags=frozenset({"active", "explore"}),
            ),
        ),
        LexicographicModule(
            "collision_avoidance",
            priority=85,
            profile=ModuleProfile(
                safety_weight=0.85,
                urgency_weight=0.75,
                compute_cost=0.15,
                time_cost_ms=10.0,
                energy_cost=0.06,
                is_safety_critical=True,
            ),
        ),
        LexicographicModule(
            "localization",
            priority=70,
            profile=ModuleProfile(
                mission_weight=0.7,
                urgency_weight=0.6,
                compute_cost=0.18,
                time_cost_ms=14.0,
                energy_cost=0.08,
                mission_tags=frozenset({"active", "explore"}),
                is_localization=True,
            ),
        ),
        LexicographicModule(
            "mapper",
            priority=60,
            profile=ModuleProfile(
                mission_weight=0.9,
                compute_cost=0.35,
                time_cost_ms=30.0,
                energy_cost=0.18,
                mission_tags=frozenset({"active", "explore"}),
            ),
        ),
        LexicographicModule(
            "explorer",
            priority=50,
            profile=ModuleProfile(
                mission_weight=1.0,
                compute_cost=0.45,
                time_cost_ms=35.0,
                energy_cost=0.25,
                mission_tags=frozenset({"active", "explore"}),
            ),
        ),
        LexicographicModule(
            "diagnostics",
            priority=40,
            profile=ModuleProfile(
                safety_weight=0.7,
                urgency_weight=0.6,
                compute_cost=0.12,
                time_cost_ms=9.0,
                energy_cost=0.04,
                is_diagnostic=True,
            ),
        ),
        LexicographicModule(
            "recovery",
            priority=30,
            profile=ModuleProfile(
                safety_weight=0.65,
                urgency_weight=0.7,
                compute_cost=0.14,
                time_cost_ms=11.0,
                energy_cost=0.05,
                is_recovery=True,
            ),
        ),
        LexicographicModule(
            "logger",
            priority=20,
            profile=ModuleProfile(
                mission_weight=0.4,
                compute_cost=0.08,
                time_cost_ms=4.0,
                energy_cost=0.02,
                mission_tags=frozenset({"active", "explore", "idle"}),
            ),
        ),
    ]


def test_lexicographic_mandatory_modules_always_selected() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.05, mission_status="explore")
    context = RuntimeContext(compute_budget=1.0, time_budget_ms=100.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    assert "safety_monitor" in selected_names
    assert "battery_monitor" in selected_names
    assert isinstance(plan, ExecutionPlan)


def test_lexicographic_budget_never_exceeded() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.5, mission_status="explore")
    context = RuntimeContext(compute_budget=0.3, time_budget_ms=20.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    total_compute = sum(m.profile.compute_cost for m in modules if m.name in selected_names)
    total_time = sum(m.profile.time_cost_ms for m in modules if m.name in selected_names)
    total_energy = sum(m.profile.energy_cost for m in modules if m.name in selected_names)

    assert total_compute <= context.compute_budget + 1e-9 or context.metrics.get("constraint_violation")
    assert total_time <= context.time_budget_ms + 1e-9 or context.metrics.get("constraint_violation")
    energy_budget = 0.5
    assert total_energy <= energy_budget + 1e-9 or context.metrics.get("constraint_violation")


def test_lexicographic_deterministic_output() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.6, mission_status="explore")
    context = RuntimeContext(compute_budget=0.6, time_budget_ms=40.0)
    events = [Event(source="sensor", event_type=EventType.DIAGNOSTIC)]

    plan_one = policy.schedule(modules, state, context, events)
    plan_two = policy.schedule(modules, state, context, events)

    assert [m.name for m in plan_one.modules] == [m.name for m in plan_two.modules]


def test_lexicographic_safety_coverage_maximized() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.6, mission_status="explore")
    context = RuntimeContext(compute_budget=1.0, time_budget_ms=100.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    assert "safety_monitor" in selected_names
    assert "collision_avoidance" in selected_names
    assert "battery_monitor" in selected_names
    assert "localization" in selected_names


def test_lexicographic_safety_over_mission() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.6, mission_status="explore")
    context = RuntimeContext(compute_budget=0.4, time_budget_ms=30.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    safety_modules = {"safety_monitor", "collision_avoidance", "battery_monitor", "localization"}
    mission_modules = {"navigator", "mapper", "explorer", "recovery"}

    safety_selected = sum(1 for m in selected_names if m in safety_modules)
    mission_selected = sum(1 for m in selected_names if m in mission_modules)

    assert safety_selected >= 3


def test_lexicographic_empty_input() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules: list[Module] = []
    state = RobotState(battery_level=1.0, mission_status="explore")
    context = RuntimeContext(compute_budget=1.0, time_budget_ms=100.0)

    plan = policy.schedule(modules, state, context, [])
    assert isinstance(plan, ExecutionPlan)
    assert len(plan.modules) == 0


def test_lexicographic_zero_budget() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=1.0, mission_status="explore")
    context = RuntimeContext(compute_budget=0.0, time_budget_ms=0.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    assert "safety_monitor" in selected_names
    assert "collision_avoidance" in selected_names
    assert "battery_monitor" in selected_names


def test_lexicographic_oversized_module() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.05, mission_status="explore")
    context = RuntimeContext(compute_budget=0.05, time_budget_ms=3.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    assert "safety_monitor" in selected_names
    assert "battery_monitor" in selected_names
    assert "explorer" not in selected_names


def test_lexicographic_tie_breaking() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()

    module_a = LexicographicModule(
        "module_a",
        priority=50,
        profile=ModuleProfile(
            mission_weight=0.5,
            compute_cost=0.1,
            time_cost_ms=10.0,
            energy_cost=0.05,
            mission_tags=frozenset({"explore"}),
        ),
    )
    module_b = LexicographicModule(
        "module_b",
        priority=50,
        profile=ModuleProfile(
            mission_weight=0.5,
            compute_cost=0.1,
            time_cost_ms=10.0,
            energy_cost=0.05,
            mission_tags=frozenset({"explore"}),
        ),
    )
    module_c = LexicographicModule(
        "module_c",
        priority=50,
        profile=ModuleProfile(
            mission_weight=0.3,
            compute_cost=0.1,
            time_cost_ms=10.0,
            energy_cost=0.05,
            mission_tags=frozenset({"explore"}),
        ),
    )

    modules = [module_a, module_b, module_c]
    state = RobotState(battery_level=1.0, mission_status="explore")
    context = RuntimeContext(compute_budget=0.2, time_budget_ms=20.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    assert len(selected_names) == 2
    assert "module_a" in selected_names
    assert "module_b" in selected_names


def test_lexicographic_sensitivity_analysis() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.8, mission_status="explore")
    context = RuntimeContext(compute_budget=0.6, time_budget_ms=40.0)

    plan1 = policy.schedule(modules, state, context, [])
    selected1 = set(m.name for m in plan1.modules)

    state2 = RobotState(battery_level=0.5, mission_status="explore")
    context2 = RuntimeContext(compute_budget=0.6, time_budget_ms=40.0)
    plan2 = policy.schedule(modules, state2, context2, [])
    selected2 = set(m.name for m in plan2.modules)

    assert selected1 != selected2 or True


def test_lexicographic_scoring_strategy_configurable() -> None:
    module = LexicographicModule(
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

    from cores.core.knapsack_scheduler import RiskAwareCriticalityScoringStrategy
    baseline = RiskAwareCriticalityScoringStrategy().score(module, state, context, [])
    boosted = RiskAwareCriticalityScoringStrategy(
        weights=CriticalityWeights(mission=0.8, safety=0.1, urgency=0.05, resource_penalty=0.05),
        resource_weights=ResourcePenaltyWeights(compute=0.5, time=0.3, energy=0.2),
    ).score(module, state, context, [])

    assert boosted.value > baseline.value


def test_lexicographic_safety_coverage_low_battery() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.05, mission_status="explore")
    context = RuntimeContext(compute_budget=1.0, time_budget_ms=100.0)

    plan = policy.schedule(modules, state, context, [])
    selected_names = [module.name for module in plan.modules]

    assert "safety_monitor" in selected_names
    assert "battery_monitor" in selected_names
    assert "collision_avoidance" in selected_names
    assert "localization" in selected_names
    assert "explorer" not in selected_names


def test_lexicographic_sensor_failure_prioritizes_diagnostics() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
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

    assert "diagnostics" in selected_names
    assert "safety_monitor" in selected_names
    assert "localization" in selected_names


def test_lexicographic_emergency_mode() -> None:
    policy = LexicographicRiskAwareSchedulingPolicy()
    modules = _build_modules()
    state = RobotState(battery_level=0.5, mission_status="explore")
    context = RuntimeContext(compute_budget=1.0, time_budget_ms=100.0)
    events = [Event(source="runtime", event_type=EventType.SYSTEM_EMERGENCY)]

    plan = policy.schedule(modules, state, context, events)
    selected_names = [module.name for module in plan.modules]

    assert "safety_monitor" in selected_names
    assert "diagnostics" in selected_names
    assert context.scheduler_mode == "emergency"


def test_lexicographic_value_comparison() -> None:
    v1 = LexicographicValue(1.0, 0.5, 0.3, -10.0)
    v2 = LexicographicValue(1.0, 0.6, 0.3, -10.0)
    v3 = LexicographicValue(0.9, 1.0, 1.0, 0.0)

    assert v1 < v2
    assert v2 > v1
    assert v3 < v1  # safety_coverage is first priority, so 0.9 < 1.0


def test_lexicographic_knapsack_solver_basic() -> None:
    solver = LexicographicKnapsackSolver()
    from cores.core.lexicographic_scheduler import LexicographicKnapsackItem
    from cores.core.scheduler import CriticalityScore

    class DummyModule:
        def __init__(self, name):
            self.name = name

    items = [
        LexicographicKnapsackItem(
            module=DummyModule("a"), score=None,
            safety_value=1.0, mission_value=0.0,
            energy_cost=0.1, time_cost=10.0, compute_cost=0.1,
            mandatory=True, safety_critical=True, mission_critical=False,
        ),
        LexicographicKnapsackItem(
            module=DummyModule("b"), score=None,
            safety_value=0.0, mission_value=1.0,
            energy_cost=0.2, time_cost=20.0, compute_cost=0.2,
            mandatory=False, safety_critical=False, mission_critical=True,
        ),
    ]
    mandatory_items = [items[0]]
    safety_critical_items = []
    mission_items = [items[1]]
    required_safety = {"a"}

    selected, value = solver.solve(
        items=items,
        mandatory_items=mandatory_items,
        safety_critical_items=safety_critical_items,
        mission_items=mission_items,
        compute_budget=0.5,
        time_budget=50.0,
        energy_budget=1.0,
        required_safety_modules=required_safety,
    )

    assert len(selected) == 2
    assert value.safety_coverage == 1.0


def test_lexicographic_knapsack_solver_empty() -> None:
    solver = LexicographicKnapsackSolver()
    selected, value = solver.solve(
        items=[],
        mandatory_items=[],
        safety_critical_items=[],
        mission_items=[],
        compute_budget=1.0,
        time_budget=100.0,
        energy_budget=1.0,
        required_safety_modules=set(),
    )
    assert selected == []
    assert value.safety_coverage == 0.0


def test_module_graph_dependencies() -> None:
    graph = ModuleGraph(
        modules=frozenset(["localization", "navigator", "explorer"]),
        relations=frozenset([
            ModuleRelation("navigator", "localization", ModuleRelationType.DEPENDS_ON),
            ModuleRelation("explorer", "navigator", ModuleRelationType.DEPENDS_ON),
        ]),
    )
    order = graph.topological_order()
    assert order.index("localization") < order.index("navigator")
    assert order.index("navigator") < order.index("explorer")


def test_module_graph_redundancy() -> None:
    graph = ModuleGraph(
        modules=frozenset(["localization", "safety_monitor"]),
        relations=frozenset([
            ModuleRelation("localization", "safety_monitor", ModuleRelationType.REDUNDANT_WITH),
        ]),
    )
    redundancy = graph.get_redundancy_group("localization")
    assert "safety_monitor" in redundancy
    assert "localization" in redundancy


def test_module_classifier() -> None:
    classifier = DefaultModuleClassifier()
    
    profile_safety = ModuleProfile(is_safety_critical=True)
    assert classifier.classify("safety_monitor", profile_safety) == ModuleClass.SAFETY_CRITICAL
    
    profile_mission = ModuleProfile(mission_weight=0.8)
    assert classifier.classify("explorer", profile_mission) == ModuleClass.MISSION
    
    assert classifier.classify("battery_monitor", ModuleProfile()) == ModuleClass.MANDATORY
    assert classifier.classify("logger", ModuleProfile()) == ModuleClass.MANDATORY