from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Callable, Optional
from collections import defaultdict
import statistics

from cores.core import (
    LexicographicRiskAwareSchedulingPolicy,
    LexicographicSelectionStrategy,
    ModuleGraph,
    ModuleRelation,
    ModuleRelationType,
    DefaultModuleClassifier,
    ModuleClass,
)
from cores.core.knapsack_scheduler import RiskAwareKnapsackSchedulingPolicy
from cores.interfaces import Module, ModuleProfile, ModuleResult, ModuleStatus
from cores.events import Event, EventType
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from benchmarks.run_benchmarks import _mission_utility, _build_scheduler_modules


class AblationType(Enum):
    FULL = "full"
    NO_DEPENDENCY_GRAPH = "no_dependency_graph"
    NO_LEXICOGRAPHIC_ORDERING = "no_lexicographic_ordering"
    NO_MANDATORY_MODULES = "no_mandatory_modules"
    NO_SAFETY_CRITICAL_DISTINCTION = "no_safety_critical_distinction"
    NO_MODULE_CLASSES = "no_module_classes"
    NO_REDUNDANCY_HANDLING = "no_redundancy_handling"
    NO_MUTUAL_EXCLUSION = "no_mutual_exclusion"
    NO_SHARED_INFO = "no_shared_info"


@dataclass
class AblationConfig:
    ablation_type: AblationType
    name: str
    modifier: Callable[[LexicographicRiskAwareSchedulingPolicy], LexicographicRiskAwareSchedulingPolicy]


def make_ablation_configs() -> List[AblationConfig]:
    def no_dep_graph(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        new_graph = ModuleGraph(
            modules=policy.module_graph.modules,
            relations=frozenset(),
        )
        return LexicographicRiskAwareSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
            module_graph=new_graph,
            classifier=policy.classifier,
        )
    
    def no_lexicographic(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        return RiskAwareKnapsackSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
        )
    
    def no_mandatory(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        class NoMandatoryClassifier(DefaultModuleClassifier):
            def classify(self, module_name: str, profile: ModuleProfile) -> ModuleClass:
                if module_name in ("battery_monitor", "logger"):
                    return ModuleClass.OPTIONAL
                return super().classify(module_name, profile)
        
        return LexicographicRiskAwareSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
            module_graph=policy.module_graph,
            classifier=NoMandatoryClassifier(),
        )
    
    def no_safety_critical(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        class NoSafetyCriticalClassifier(DefaultModuleClassifier):
            def classify(self, module_name: str, profile: ModuleProfile) -> ModuleClass:
                if module_name in ("safety_monitor", "collision_avoidance", "localization"):
                    return ModuleClass.MISSION
                return super().classify(module_name, profile)
        
        return LexicographicRiskAwareSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
            module_graph=policy.module_graph,
            classifier=NoSafetyCriticalClassifier(),
        )
    
    def no_module_classes(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        class FlatClassifier(DefaultModuleClassifier):
            def classify(self, module_name: str, profile: ModuleProfile) -> ModuleClass:
                if module_name in ("battery_monitor", "logger"):
                    return ModuleClass.MANDATORY
                return ModuleClass.MISSION
        
        return LexicographicRiskAwareSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
            module_graph=policy.module_graph,
            classifier=FlatClassifier(),
        )
    
    def no_redundancy(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        new_relations = frozenset(
            r for r in policy.module_graph.relations
            if r.relation_type != ModuleRelationType.REDUNDANT_WITH
        )
        new_graph = ModuleGraph(
            modules=policy.module_graph.modules,
            relations=new_relations,
        )
        return LexicographicRiskAwareSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
            module_graph=new_graph,
            classifier=policy.classifier,
        )
    
    def no_mutual_exclusion(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        new_relations = frozenset(
            r for r in policy.module_graph.relations
            if r.relation_type != ModuleRelationType.MUTUALLY_EXCLUSIVE
        )
        new_graph = ModuleGraph(
            modules=policy.module_graph.modules,
            relations=new_relations,
        )
        return LexicographicRiskAwareSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
            module_graph=new_graph,
            classifier=policy.classifier,
        )
    
    def no_shared_info(policy: LexicographicRiskAwareSchedulingPolicy) -> LexicographicRiskAwareSchedulingPolicy:
        new_relations = frozenset(
            r for r in policy.module_graph.relations
            if r.relation_type != ModuleRelationType.SHARES_INFO_WITH
        )
        new_graph = ModuleGraph(
            modules=policy.module_graph.modules,
            relations=new_relations,
        )
        return LexicographicRiskAwareSchedulingPolicy(
            scoring_strategy=policy.scoring_strategy,
            module_graph=new_graph,
            classifier=policy.classifier,
        )
    
    return [
        AblationConfig(
            AblationType.NO_DEPENDENCY_GRAPH,
            "No Dependency Graph",
            no_dep_graph,
        ),
        AblationConfig(
            AblationType.NO_LEXICOGRAPHIC_ORDERING,
            "No Lexicographic Ordering",
            no_lexicographic,
        ),
        AblationConfig(
            AblationType.NO_MANDATORY_MODULES,
            "No Mandatory Modules",
            no_mandatory,
        ),
        AblationConfig(
            AblationType.NO_SAFETY_CRITICAL_DISTINCTION,
            "No Safety-Critical Distinction",
            no_safety_critical,
        ),
        AblationConfig(
            AblationType.NO_MODULE_CLASSES,
            "No Module Classes (Flat)",
            no_module_classes,
        ),
        AblationConfig(
            AblationType.NO_REDUNDANCY_HANDLING,
            "No Redundancy Handling",
            no_redundancy,
        ),
        AblationConfig(
            AblationType.NO_MUTUAL_EXCLUSION,
            "No Mutual Exclusion",
            no_mutual_exclusion,
        ),
        AblationConfig(
            AblationType.NO_SHARED_INFO,
            "No Shared Information",
            no_shared_info,
        ),
    ]


@dataclass(frozen=True)
class AblationResult:
    ablation_type: AblationType
    scenario_name: str
    safety_coverage: float
    mission_utility: float
    energy_headroom: float
    decision_time_ms: float
    selected_modules: List[str]


def _build_test_modules() -> List[Module]:
    class TestModule(Module):
        def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
            return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)
    
    return [
        TestModule(
            "safety_monitor",
            priority=100,
            profile=ModuleProfile(safety_weight=0.9, urgency_weight=0.8, compute_cost=0.1, time_cost_ms=8.0, energy_cost=0.05, is_safety_critical=True),
        ),
        TestModule(
            "battery_monitor",
            priority=90,
            profile=ModuleProfile(safety_weight=0.8, urgency_weight=0.7, compute_cost=0.05, time_cost_ms=5.0, energy_cost=0.02, is_safety_critical=True),
        ),
        TestModule(
            "navigator",
            priority=80,
            profile=ModuleProfile(mission_weight=0.8, urgency_weight=0.5, compute_cost=0.15, time_cost_ms=12.0, energy_cost=0.08, mission_tags=frozenset({"active", "explore"})),
        ),
        TestModule(
            "collision_avoidance",
            priority=85,
            profile=ModuleProfile(safety_weight=0.85, urgency_weight=0.75, compute_cost=0.15, time_cost_ms=10.0, energy_cost=0.06, is_safety_critical=True),
        ),
        TestModule(
            "localization",
            priority=70,
            profile=ModuleProfile(mission_weight=0.7, urgency_weight=0.6, compute_cost=0.18, time_cost_ms=14.0, energy_cost=0.08, mission_tags=frozenset({"active", "explore"}), is_localization=True),
        ),
        TestModule(
            "mapper",
            priority=60,
            profile=ModuleProfile(mission_weight=0.9, compute_cost=0.35, time_cost_ms=30.0, energy_cost=0.18, mission_tags=frozenset({"active", "explore"})),
        ),
        TestModule(
            "explorer",
            priority=50,
            profile=ModuleProfile(mission_weight=1.0, compute_cost=0.45, time_cost_ms=35.0, energy_cost=0.25, mission_tags=frozenset({"active", "explore"})),
        ),
        TestModule(
            "diagnostics",
            priority=40,
            profile=ModuleProfile(safety_weight=0.7, urgency_weight=0.6, compute_cost=0.12, time_cost_ms=9.0, energy_cost=0.04, is_diagnostic=True),
        ),
        TestModule(
            "recovery",
            priority=30,
            profile=ModuleProfile(safety_weight=0.65, urgency_weight=0.7, compute_cost=0.14, time_cost_ms=11.0, energy_cost=0.05, is_recovery=True),
        ),
        TestModule(
            "logger",
            priority=20,
            profile=ModuleProfile(mission_weight=0.4, compute_cost=0.08, time_cost_ms=4.0, energy_cost=0.02, mission_tags=frozenset({"active", "explore", "idle"})),
        ),
    ]


def run_ablation_study(
    base_policy: LexicographicRiskAwareSchedulingPolicy,
    modules: List[Module],
    scenarios: List,
) -> List[AblationResult]:
    configs = make_ablation_configs()
    results = []
    
    for config in configs:
        ablated_policy = config.modifier(base_policy)
        
        for scenario in scenarios:
            state = scenario.state.model_copy(deep=True)
            context = scenario.context.model_copy(deep=True)
            events = list(scenario.events)
            
            plan = ablated_policy.schedule(modules, state, context, events)
            selected = [m.name for m in plan.modules]
            
            safety_cov = sum(1 for m in selected if m in scenario.required_modules) / max(1, len(scenario.required_modules))
            
            mission_util = _mission_utility(modules, selected, state.mission_status.lower())
            
            total_energy = sum(m.profile.energy_cost for m in modules if m.name in selected)
            battery = state.battery_level
            energy_budget = 0.2 if battery < 0.10 else (0.5 if battery < 0.30 else 1.0)
            energy_headroom = max(0.0, energy_budget - total_energy) / max(energy_budget, 1e-9)
            
            decision_time = context.metrics.get("decision_time_ms", 0.0)
            
            results.append(AblationResult(
                ablation_type=config.ablation_type,
                scenario_name=scenario.name,
                safety_coverage=safety_cov,
                mission_utility=mission_util,
                energy_headroom=energy_headroom,
                decision_time_ms=decision_time,
                selected_modules=selected,
            ))
    
    base_results = run_single_policy(base_policy, modules, scenarios, AblationType.FULL)
    results.extend(base_results)
    
    return results


def run_single_policy(
    policy,
    modules: List[Module],
    scenarios: List,
    ablation_type: AblationType,
) -> List[AblationResult]:
    results = []
    for scenario in scenarios:
        state = scenario.state.model_copy(deep=True)
        context = scenario.context.model_copy(deep=True)
        events = list(scenario.events)
        
        plan = policy.schedule(modules, state, context, events)
        selected = [m.name for m in plan.modules]
        
        safety_cov = sum(1 for m in selected if m in scenario.required_modules) / max(1, len(scenario.required_modules))
        
        mission_util = _mission_utility(modules, selected, state.mission_status.lower())
        
        total_energy = sum(m.profile.energy_cost for m in modules if m.name in selected)
        battery = state.battery_level
        energy_budget = 0.2 if battery < 0.10 else (0.5 if battery < 0.30 else 1.0)
        energy_headroom = max(0.0, energy_budget - total_energy) / max(energy_budget, 1e-9)
        
        decision_time = context.metrics.get("decision_time_ms", 0.0)
        
        decision_time = context.metrics.get("decision_time_ms", 0.0)
        
        results.append(AblationResult(
            ablation_type=ablation_type,
            scenario_name=scenario.name,
            safety_coverage=safety_cov,
            mission_utility=mission_util,
            energy_headroom=energy_headroom,
            decision_time_ms=decision_time,
            selected_modules=selected,
        ))
    return results


def aggregate_ablation_results(results: List[AblationResult]) -> Dict:
    grouped = defaultdict(lambda: defaultdict(list))
    
    for r in results:
        grouped[r.ablation_type]["safety_coverage"].append(r.safety_coverage)
        grouped[r.ablation_type]["mission_utility"].append(r.mission_utility)
        grouped[r.ablation_type]["energy_headroom"].append(r.energy_headroom)
        grouped[r.ablation_type]["decision_time_ms"].append(r.decision_time_ms)
    
    summary = {}
    for atype, metrics in grouped.items():
        summary[atype] = {
            "count": len(metrics["safety_coverage"]),
            "safety_coverage": {
                "mean": statistics.mean(metrics["safety_coverage"]),
                "std": statistics.stdev(metrics["safety_coverage"]) if len(metrics["safety_coverage"]) > 1 else 0.0,
                "min": min(metrics["safety_coverage"]),
                "max": max(metrics["safety_coverage"]),
            },
            "mission_utility": {
                "mean": statistics.mean(metrics["mission_utility"]),
                "std": statistics.stdev(metrics["mission_utility"]) if len(metrics["mission_utility"]) > 1 else 0.0,
                "min": min(metrics["mission_utility"]),
                "max": max(metrics["mission_utility"]),
            },
            "energy_headroom": {
                "mean": statistics.mean(metrics["energy_headroom"]),
                "std": statistics.stdev(metrics["energy_headroom"]) if len(metrics["energy_headroom"]) > 1 else 0.0,
                "min": min(metrics["energy_headroom"]),
                "max": max(metrics["energy_headroom"]),
            },
            "decision_time_ms": {
                "mean": statistics.mean(metrics["decision_time_ms"]),
                "std": statistics.stdev(metrics["decision_time_ms"]) if len(metrics["decision_time_ms"]) > 1 else 0.0,
                "min": min(metrics["decision_time_ms"]),
                "max": max(metrics["decision_time_ms"]),
            },
        }
    
    return summary


def compute_ablation_impact(summary: Dict) -> Dict:
    if AblationType.FULL not in summary:
        return {}
    
    baseline = summary[AblationType.FULL]
    impact = {}
    
    for atype in summary:
        if atype == AblationType.FULL:
            continue
        
        metrics = summary[atype]
        impact[atype] = {
            "safety_coverage_delta": metrics["safety_coverage"]["mean"] - baseline["safety_coverage"]["mean"],
            "mission_utility_delta": metrics["mission_utility"]["mean"] - baseline["mission_utility"]["mean"],
            "energy_headroom_delta": metrics["energy_headroom"]["mean"] - baseline["energy_headroom"]["mean"],
            "decision_time_delta": metrics["decision_time_ms"]["mean"] - baseline["decision_time_ms"]["mean"],
            "relative_safety": metrics["safety_coverage"]["mean"] / max(baseline["safety_coverage"]["mean"], 1e-9),
            "relative_mission": metrics["mission_utility"]["mean"] / max(baseline["mission_utility"]["mean"], 1e-9),
            "relative_energy": metrics["energy_headroom"]["mean"] / max(baseline["energy_headroom"]["mean"], 1e-9),
        }
    
    return impact