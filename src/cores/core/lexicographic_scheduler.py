from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict

from cores.core.scheduler import (
    CriticalityScoringStrategy,
    CriticalityScore,
    CriticalityWeights,
    ResourcePenaltyWeights,
    ModuleSelectionStrategy,
    SchedulingPolicy,
)
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_plan import ExecutionPlan
from cores.events.event import Event
from cores.interfaces.module import Module
from cores.core.module_graph import (
    ModuleGraph, ModuleRelation, ModuleRelationType, ModuleClassifier,
    DefaultModuleClassifier, ModuleClass, ModuleProfile
)


@dataclass(frozen=True)
class LexicographicValue:
    safety_coverage: float
    mission_utility: float
    energy_headroom: float
    neg_time: float
    
    def __lt__(self, other: 'LexicographicValue') -> bool:
        if abs(self.safety_coverage - other.safety_coverage) > 1e-9:
            return self.safety_coverage < other.safety_coverage
        if abs(self.mission_utility - other.mission_utility) > 1e-9:
            return self.mission_utility < other.mission_utility
        if abs(self.energy_headroom - other.energy_headroom) > 1e-9:
            return self.energy_headroom < other.energy_headroom
        return self.neg_time < other.neg_time
    
    def __eq__(self, other: 'LexicographicValue') -> bool:
        return (abs(self.safety_coverage - other.safety_coverage) < 1e-9 and
                abs(self.mission_utility - other.mission_utility) < 1e-9 and
                abs(self.energy_headroom - other.energy_headroom) < 1e-9 and
                abs(self.neg_time - other.neg_time) < 1e-9)
    
    def __le__(self, other: 'LexicographicValue') -> bool:
        return self < other or self == other
    
    def dominates(self, other: 'LexicographicValue') -> bool:
        return other < self


@dataclass(frozen=True)
class LexicographicKnapsackItem:
    module: Module
    score: CriticalityScore
    safety_value: float
    mission_value: float
    energy_cost: float
    time_cost: float
    compute_cost: float
    mandatory: bool
    safety_critical: bool
    mission_critical: bool


class LexicographicKnapsackSolver:
    def solve(
        self,
        items: List[LexicographicKnapsackItem],
        mandatory_items: List[LexicographicKnapsackItem],
        safety_critical_items: List[LexicographicKnapsackItem],
        mission_items: List[LexicographicKnapsackItem],
        compute_budget: float,
        time_budget: float,
        energy_budget: float,
        required_safety_modules: Set[str],
    ) -> Tuple[List[LexicographicKnapsackItem], LexicographicValue]:
        
        all_mandatory = mandatory_items + safety_critical_items
        
        mandatory_compute = sum(m.compute_cost for m in all_mandatory)
        mandatory_time = sum(m.time_cost for m in all_mandatory)
        mandatory_energy = sum(m.energy_cost for m in all_mandatory)
        
        if (mandatory_compute > compute_budget or 
            mandatory_time > time_budget or 
            mandatory_energy > energy_budget):
            pass
        
        remaining_compute = max(0.0, compute_budget - mandatory_compute)
        remaining_time = max(0.0, time_budget - mandatory_time)
        remaining_energy = max(0.0, energy_budget - mandatory_energy)
        
        optional_items = [m for m in items if not m.mandatory and not m.safety_critical]
        
        selected_optional = self._lexicographic_knapsack(
            optional_items,
            remaining_compute,
            remaining_time,
            remaining_energy,
        )
        
        all_selected = all_mandatory + selected_optional
        
        safety_covered = {m.module.name for m in all_selected if m.safety_critical or m.mandatory}
        safety_coverage = len(safety_covered & required_safety_modules) / max(1, len(required_safety_modules))
        
        total_mission_value = sum(m.mission_value for m in all_selected)
        max_mission_value = sum(m.mission_value for m in all_mandatory + optional_items + mission_items)
        mission_utility = total_mission_value / max(max_mission_value, 1e-9)
        
        total_energy = sum(m.energy_cost for m in all_selected)
        energy_headroom = max(0.0, energy_budget - total_energy) / max(energy_budget, 1e-9)
        
        total_time = sum(m.time_cost for m in all_selected)
        neg_time = -total_time
        
        value = LexicographicValue(
            safety_coverage=safety_coverage,
            mission_utility=mission_utility,
            energy_headroom=energy_headroom,
            neg_time=neg_time,
        )
        
        return all_selected, value
    
    def _lexicographic_knapsack(
        self,
        items: List[LexicographicKnapsackItem],
        compute_budget: float,
        time_budget: float,
        energy_budget: float,
    ) -> List[LexicographicKnapsackItem]:
        
        if not items:
            return []
        
        c_scale = 1000
        t_scale = 1
        e_scale = 1000
        
        c_budget = int(compute_budget * c_scale)
        t_budget = int(time_budget * t_scale)
        e_budget = int(energy_budget * e_scale)
        
        dp = defaultdict(list)
        dp[(0, 0, 0)] = [LexicographicValue(0.0, 0.0, 0.0, 0.0)]
        
        item_infos = []
        for item in items:
            item_infos.append({
                'item': item,
                'c': int(item.compute_cost * c_scale),
                't': int(item.time_cost * t_scale),
                'e': int(item.energy_cost * e_scale),
                'safety_v': item.safety_value,
                'mission_v': item.mission_value,
                'energy_v': -item.energy_cost,
                'time_v': -item.time_cost,
            })
        
        for info in item_infos:
            new_dp = defaultdict(list)
            for state, values in dp.items():
                for v in values:
                    new_dp[state].append(v)
            
            for (c, t, e), values in dp.items():
                nc = c + info['c']
                nt = t + info['t']
                ne = e + info['e']
                
                if nc <= c_budget and nt <= t_budget and ne <= e_budget:
                    for v in values:
                        nv = LexicographicValue(
                            safety_coverage=v.safety_coverage + info['safety_v'],
                            mission_utility=v.mission_utility + info['mission_v'],
                            energy_headroom=v.energy_headroom + info['energy_v'],
                            neg_time=v.neg_time + info['time_v'],
                        )
                        new_dp[(nc, nt, ne)].append(nv)
            
            for state, values in new_dp.items():
                pareto = []
                for v in values:
                    if not any(other.dominates(v) for other in pareto):
                        pareto = [x for x in pareto if not v.dominates(x)]
                        pareto.append(v)
                dp[state] = pareto
        
        best_value = LexicographicValue(-1, -1, -1, -1)
        best_state = None
        
        for state, values in dp.items():
            for v in values:
                if best_value < v:
                    best_value = v
                    best_state = state
        
        if best_state is None:
            return []
        
        selected = []
        c, t, e = best_state
        remaining_items = list(reversed(item_infos))
        
        while (c, t, e) != (0, 0, 0) and remaining_items:
            info = remaining_items.pop()
            prev_c = c - info['c']
            prev_t = t - info['t']
            prev_e = e - info['e']
            
            if prev_c >= 0 and prev_t >= 0 and prev_e >= 0 and (prev_c, prev_t, prev_e) in dp:
                for v in dp[(prev_c, prev_t, prev_e)]:
                    nv = LexicographicValue(
                        safety_coverage=v.safety_coverage + info['safety_v'],
                        mission_utility=v.mission_utility + info['mission_v'],
                        energy_headroom=v.energy_headroom + info['energy_v'],
                        neg_time=v.neg_time + info['time_v'],
                    )
                    if any(abs(nv.safety_coverage - bv.safety_coverage) < 1e-9 and
                           abs(nv.mission_utility - bv.mission_utility) < 1e-9 and
                           abs(nv.energy_headroom - bv.energy_headroom) < 1e-9 and
                           abs(nv.neg_time - bv.neg_time) < 1e-9
                           for bv in dp[(c, t, e)]):
                        selected.append(info['item'])
                        c, t, e = prev_c, prev_t, prev_e
                        break
        
        return selected


class LexicographicSelectionStrategy(ModuleSelectionStrategy):
    def __init__(
        self,
        solver: Optional[LexicographicKnapsackSolver] = None,
        classifier: Optional[ModuleClassifier] = None,
        module_graph: Optional[ModuleGraph] = None,
    ):
        self.solver = solver or LexicographicKnapsackSolver()
        self.classifier = classifier or DefaultModuleClassifier()
        self.module_graph = module_graph
    
    def select(
        self,
        modules: List[Module],
        scores: Dict[str, CriticalityScore],
        state: RobotState,
        context: RuntimeContext,
    ) -> ExecutionPlan:
        energy_budget = self._energy_budget(state.battery_level)
        
        mandatory_items = []
        safety_critical_items = []
        mission_items = []
        optional_items = []
        
        required_safety = {m.name for m in modules if m.profile.is_safety_critical}
        
        for module in modules:
            score = scores[module.name]
            profile = module.profile
            module_class = self.classifier.classify(module.name, profile)
            
            safety_value = score.safety_factor if module_class == ModuleClass.SAFETY_CRITICAL else 0.0
            mission_value = score.mission_factor if module_class == ModuleClass.MISSION else 0.0
            
            item = LexicographicKnapsackItem(
                module=module,
                score=score,
                safety_value=safety_value,
                mission_value=mission_value,
                energy_cost=profile.energy_cost,
                time_cost=profile.time_cost_ms,
                compute_cost=profile.compute_cost,
                mandatory=(module_class == ModuleClass.MANDATORY or score.mandatory),
                safety_critical=(module_class == ModuleClass.SAFETY_CRITICAL),
                mission_critical=(module_class == ModuleClass.MISSION),
            )
            
            if item.mandatory:
                mandatory_items.append(item)
            elif item.safety_critical:
                safety_critical_items.append(item)
            elif item.mission_critical:
                mission_items.append(item)
            else:
                optional_items.append(item)
        
        all_items = mandatory_items + safety_critical_items + mission_items + optional_items
        
        selected_items, value = self.solver.solve(
            items=all_items,
            mandatory_items=mandatory_items,
            safety_critical_items=safety_critical_items,
            mission_items=mission_items,
            compute_budget=context.compute_budget,
            time_budget=context.time_budget_ms,
            energy_budget=energy_budget,
            required_safety_modules=required_safety,
        )
        
        selected_items.sort(key=lambda x: (
            0 if x.mandatory else (1 if x.safety_critical else (2 if x.mission_critical else 3)),
            -x.score.value,
            x.module.priority,
        ))
        
        selected_modules = [item.module for item in selected_items]
        
        context.metrics["selected"] = [m.name for m in selected_modules]
        context.metrics["deferred"] = [m.name for m in modules if m.name not in context.metrics["selected"]]
        context.metrics["resource_usage"] = {
            "compute": sum(m.module.profile.compute_cost for m in selected_items),
            "time_ms": sum(m.module.profile.time_cost_ms for m in selected_items),
            "energy": sum(m.module.profile.energy_cost for m in selected_items),
        }
        context.metrics["constraints_active"] = [
            name for name, active in (
                ("compute", context.compute_budget < 1.0),
                ("time", context.time_budget_ms < 100.0),
                ("battery", energy_budget < 1.0),
            ) if active
        ]
        total_compute = sum(m.module.profile.compute_cost for m in selected_items)
        total_time = sum(m.module.profile.time_cost_ms for m in selected_items)
        total_energy = sum(m.module.profile.energy_cost for m in selected_items)
        context.metrics["constraint_violation"] = any((
            total_compute > context.compute_budget,
            total_time > context.time_budget_ms,
            total_energy > energy_budget,
        ))
        context.metrics["lexicographic_value"] = {
            "safety_coverage": value.safety_coverage,
            "mission_utility": value.mission_utility,
            "energy_headroom": value.energy_headroom,
            "neg_time": value.neg_time,
        }
        
        return ExecutionPlan(modules=selected_modules)
    
    @staticmethod
    def _energy_budget(battery_level: float) -> float:
        if battery_level < 0.10:
            return 0.2
        if battery_level < 0.30:
            return 0.5
        return 1.0


class LexicographicRiskAwareSchedulingPolicy(SchedulingPolicy):
    def __init__(
        self,
        scoring_strategy: Optional[CriticalityScoringStrategy] = None,
        selection_strategy: Optional[ModuleSelectionStrategy] = None,
        module_graph: Optional[ModuleGraph] = None,
        classifier: Optional[ModuleClassifier] = None,
    ) -> None:
        from cores.core.knapsack_scheduler import RiskAwareCriticalityScoringStrategy
        self.scoring_strategy = scoring_strategy or RiskAwareCriticalityScoringStrategy()
        self.module_graph = module_graph or self._build_default_graph()
        self.classifier = classifier or DefaultModuleClassifier()
        self.selection_strategy = selection_strategy or LexicographicSelectionStrategy(
            module_graph=self.module_graph,
            classifier=self.classifier,
        )
    
    def _build_default_graph(self) -> ModuleGraph:
        modules = frozenset([
            "safety_monitor", "battery_monitor", "navigator", "collision_avoidance",
            "localization", "mapper", "explorer", "diagnostics", "recovery", "logger"
        ])
        
        relations = frozenset([
            ModuleRelation("navigator", "localization", ModuleRelationType.DEPENDS_ON),
            ModuleRelation("explorer", "navigator", ModuleRelationType.DEPENDS_ON),
            ModuleRelation("mapper", "localization", ModuleRelationType.DEPENDS_ON),
            ModuleRelation("recovery", "diagnostics", ModuleRelationType.DEPENDS_ON),
            ModuleRelation("localization", "safety_monitor", ModuleRelationType.REDUNDANT_WITH),
            ModuleRelation("navigator", "collision_avoidance", ModuleRelationType.MUTUALLY_EXCLUSIVE),
            ModuleRelation("mapper", "explorer", ModuleRelationType.SHARES_INFO_WITH),
        ])
        
        return ModuleGraph(modules=modules, relations=relations)
    
    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        from time import perf_counter
        
        started_at = perf_counter()
        scored_modules = [
            (module, self.scoring_strategy.score(module, state, context, events))
            for module in modules
        ]
        scores_by_name = {module.name: score for module, score in scored_modules}
        
        context.scheduler_mode = self._resolve_mode(state, context, events)
        context.is_emergency = context.scheduler_mode == "emergency"
        context.metrics["policy"] = "lexicographic_risk_aware"
        context.metrics["mode"] = context.scheduler_mode
        context.metrics["scores"] = {
            module.name: {
                "value": score.value,
                "safety_factor": score.safety_factor,
                "mission_factor": score.mission_factor,
                "urgency_factor": score.urgency_factor,
                "resource_penalty": score.resource_penalty,
                "mandatory": score.mandatory,
            }
            for module, score in scored_modules
        }
        
        plan = self.selection_strategy.select(modules, scores_by_name, state, context)
        context.metrics["decision_time_ms"] = (perf_counter() - started_at) * 1000.0
        return plan
    
    @staticmethod
    def _resolve_mode(
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> str:
        from cores.events.event_type import EventType
        
        if context.is_emergency or any(
            event.event_type is EventType.SYSTEM_EMERGENCY for event in events
        ):
            return "emergency"
        if state.battery_level < 0.30:
            return "low_power"
        return "default"