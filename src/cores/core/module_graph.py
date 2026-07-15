from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Dict, List, Set, Optional, FrozenSet
from frozendict import frozendict


class ModuleRelationType(StrEnum):
    DEPENDS_ON = "depends_on"
    REDUNDANT_WITH = "redundant_with"
    MUTUALLY_EXCLUSIVE = "mutually_exclusive"
    SHARES_INFO_WITH = "shares_info_with"
    PREREQUISITE_FOR = "prerequisite_for"


@dataclass(frozen=True)
class ModuleRelation:
    source: str
    target: str
    relation_type: ModuleRelationType
    weight: float = 1.0


@dataclass(frozen=True)
class ModuleGraph:
    modules: FrozenSet[str]
    relations: FrozenSet[ModuleRelation]
    
    def get_dependencies(self, module: str) -> Set[str]:
        return {r.target for r in self.relations 
                if r.source == module and r.relation_type == ModuleRelationType.DEPENDS_ON}
    
    def get_dependents(self, module: str) -> Set[str]:
        return {r.source for r in self.relations 
                if r.target == module and r.relation_type == ModuleRelationType.DEPENDS_ON}
    
    def get_redundancy_group(self, module: str) -> Set[str]:
        group = {module}
        for r in self.relations:
            if r.relation_type == ModuleRelationType.REDUNDANT_WITH:
                if r.source == module:
                    group.add(r.target)
                elif r.target == module:
                    group.add(r.source)
        return group
    
    def get_mutual_exclusions(self, module: str) -> Set[str]:
        excluded = set()
        for r in self.relations:
            if r.relation_type == ModuleRelationType.MUTUALLY_EXCLUSIVE:
                if r.source == module:
                    excluded.add(r.target)
                elif r.target == module:
                    excluded.add(r.source)
        return excluded
    
    def get_shared_info(self, module: str) -> Set[str]:
        shared = set()
        for r in self.relations:
            if r.relation_type == ModuleRelationType.SHARES_INFO_WITH:
                if r.source == module:
                    shared.add(r.target)
                elif r.target == module:
                    shared.add(r.source)
        return shared
    
    def topological_order(self) -> List[str]:
        in_degree = {m: 0 for m in self.modules}
        adj = {m: [] for m in self.modules}
        
        for r in self.relations:
            if r.relation_type == ModuleRelationType.DEPENDS_ON:
                adj[r.target].append(r.source)
                in_degree[r.source] += 1
        
        queue = [m for m in self.modules if in_degree[m] == 0]
        result = []
        
        while queue:
            queue.sort()
            m = queue.pop(0)
            result.append(m)
            for dep in adj[m]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
        
        if len(result) != len(self.modules):
            remaining = self.modules - set(result)
            result.extend(sorted(remaining))
        
        return result


class ModuleClassifier(ABC):
    @abstractmethod
    def classify(self, module_name: str, profile: ModuleProfile) -> ModuleClass:
        pass


class ModuleClass(StrEnum):
    MANDATORY = "mandatory"
    SAFETY_CRITICAL = "safety_critical"
    MISSION = "mission"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class ModuleProfile:
    safety_weight: float = 0.0
    mission_weight: float = 0.0
    urgency_weight: float = 0.0
    compute_cost: float = 0.0
    time_cost_ms: float = 0.0
    energy_cost: float = 0.0
    mission_tags: FrozenSet[str] = field(default_factory=frozenset)
    is_safety_critical: bool = False
    is_diagnostic: bool = False
    is_recovery: bool = False
    is_localization: bool = False


@dataclass(frozen=True)
class DefaultModuleClassifier(ModuleClassifier):
    def classify(self, module_name: str, profile: ModuleProfile) -> ModuleClass:
        if module_name in ("battery_monitor", "logger"):
            return ModuleClass.MANDATORY
        if profile.is_safety_critical or module_name in ("localization", "collision_avoidance", "safety_monitor"):
            return ModuleClass.SAFETY_CRITICAL
        if profile.mission_weight > 0 or module_name in ("explorer", "mapper", "recovery", "navigator"):
            return ModuleClass.MISSION
        return ModuleClass.OPTIONAL