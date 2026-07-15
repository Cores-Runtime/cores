from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple

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


@dataclass(frozen=True)
class KnapsackItem:
    module: Module
    score: CriticalityScore
    value: float
    compute_cost: float
    time_cost: float
    energy_cost: float
    mandatory: bool


class KnapsackSolver(ABC):
    @abstractmethod
    def solve(
        self,
        items: List[KnapsackItem],
        compute_budget: float,
        time_budget: float,
        energy_budget: float,
    ) -> Tuple[List[KnapsackItem], float]:
        pass


class ExactKnapsackSolver(KnapsackSolver):
    def solve(
        self,
        items: List[KnapsackItem],
        compute_budget: float,
        time_budget: float,
        energy_budget: float,
    ) -> Tuple[List[KnapsackItem], float]:
        n = len(items)
        if n == 0:
            return [], 0.0

        c_budget = int(compute_budget * 1000)
        t_budget = int(time_budget)
        e_budget = int(energy_budget * 1000)

        c_costs = [int(item.compute_cost * 1000) for item in items]
        t_costs = [int(item.time_cost) for item in items]
        e_costs = [int(item.energy_cost * 1000) for item in items]
        values = [item.value for item in items]

        dp = {}
        dp[(0, 0, 0)] = (0.0, -1)

        for i in range(n):
            new_dp = dp.copy()
            c_i = c_costs[i]
            t_i = t_costs[i]
            e_i = e_costs[i]
            v_i = values[i]

            for (c, t, e), (val, prev) in dp.items():
                nc = c + c_i
                nt = t + t_i
                ne = e + e_i

                if nc <= c_budget and nt <= t_budget and ne <= e_budget:
                    nval = val + v_i
                    key = (nc, nt, ne)
                    if key not in new_dp or new_dp[key][0] < nval - 1e-9:
                        new_dp[key] = (nval, i)
                    elif abs(new_dp[key][0] - nval) < 1e-9 and new_dp[key][1] > i:
                        new_dp[key] = (nval, i)

            dp = new_dp

        best_val = -1.0
        best_key = None
        for key, (val, _) in dp.items():
            if val > best_val + 1e-9:
                best_val = val
                best_key = key
            elif abs(val - best_val) < 1e-9 and key is not None:
                if best_key is not None:
                    if key[0] < best_key[0] or (
                        key[0] == best_key[0] and key[1] < best_key[1]
                    ) or (
                        key[0] == best_key[0]
                        and key[1] == best_key[1]
                        and key[2] < best_key[2]
                    ):
                        best_key = key

        if best_val <= 0 or best_key is None:
            return [], 0.0

        selected_indices = []
        c, t, e = best_key
        while (c, t, e) in dp and dp[(c, t, e)][1] != -1:
            idx = dp[(c, t, e)][1]
            selected_indices.append(idx)
            c -= c_costs[idx]
            t -= t_costs[idx]
            e -= e_costs[idx]

        selected_indices.sort(key=lambda idx: (items[idx].score.value, -items[idx].module.priority), reverse=True)

        selected_items = [items[i] for i in selected_indices]
        return selected_items, best_val


class ExactKnapsackSolverSimple:
    """Simplified 0/1 knapsack solver for testing (single budget dimension)."""

    def solve(self, items: List[Dict], capacity: float) -> Dict:
        n = len(items)
        if n == 0 or capacity <= 0:
            return {"value": 0.0, "weight": 0.0, "selected": []}

        cap = int(capacity * 1000)
        weights = [int(item["weight"] * 1000) for item in items]
        values = [item["value"] for item in items]

        dp = [0.0] * (cap + 1)
        choice = [-1] * (cap + 1)

        for i in range(n):
            w = weights[i]
            v = values[i]
            for c in range(cap, w - 1, -1):
                if dp[c - w] + v > dp[c] + 1e-9:
                    dp[c] = dp[c - w] + v
                    choice[c] = i
                elif abs(dp[c - w] + v - dp[c]) < 1e-9 and choice[c] > i:
                    choice[c] = i

        best_c = max(range(cap + 1), key=lambda c: (dp[c], -c))
        best_val = dp[best_c]

        if best_val <= 0:
            return {"value": 0.0, "weight": 0.0, "selected": []}

        selected = []
        c = best_c
        while c > 0 and choice[c] != -1:
            idx = choice[c]
            selected.append(idx)
            c -= weights[idx]

        selected.reverse()
        total_weight = sum(weights[i] for i in selected) / 1000.0

        return {
            "value": best_val,
            "weight": total_weight,
            "selected": [items[i]["id"] for i in selected],
        }


class KnapsackSelectionStrategy(ModuleSelectionStrategy):
    def __init__(self, solver: KnapsackSolver | None = None):
        self.solver = solver or ExactKnapsackSolver()

    def select(
        self,
        modules: List[Module],
        scores: Dict[str, CriticalityScore],
        state: RobotState,
        context: RuntimeContext,
    ) -> ExecutionPlan:
        energy_budget = self._energy_budget(state.battery_level)

        items = []
        mandatory_items = []

        for module in modules:
            score = scores[module.name]
            profile = module.profile

            item = KnapsackItem(
                module=module,
                score=score,
                value=max(0.0, score.value),
                compute_cost=profile.compute_cost,
                time_cost=profile.time_cost_ms,
                energy_cost=profile.energy_cost,
                mandatory=score.mandatory,
            )

            if score.mandatory:
                mandatory_items.append(item)
            else:
                items.append(item)

        mandatory_compute = sum(m.compute_cost for m in mandatory_items)
        mandatory_time = sum(m.time_cost for m in mandatory_items)
        mandatory_energy = sum(m.energy_cost for m in mandatory_items)

        remaining_compute = max(0.0, context.compute_budget - mandatory_compute)
        remaining_time = max(0.0, context.time_budget_ms - mandatory_time)
        remaining_energy = max(0.0, energy_budget - mandatory_energy)

        optional_selected, _ = self.solver.solve(
            items,
            remaining_compute,
            remaining_time,
            remaining_energy,
        )

        all_selected = mandatory_items + optional_selected
        all_selected.sort(key=lambda x: (x.score.value, -x.module.priority), reverse=True)

        selected_modules = [item.module for item in all_selected]

        context.metrics["selected"] = [module.name for module in selected_modules]
        context.metrics["deferred"] = [
            module.name
            for module in modules
            if module.name not in context.metrics["selected"]
        ]
        context.metrics["resource_usage"] = {
            "compute": sum(m.module.profile.compute_cost for m in all_selected),
            "time_ms": sum(m.module.profile.time_cost_ms for m in all_selected),
            "energy": sum(m.module.profile.energy_cost for m in all_selected),
        }
        context.metrics["constraints_active"] = [
            name
            for name, active in (
                ("compute", context.compute_budget < 1.0),
                ("time", context.time_budget_ms < 100.0),
                ("battery", energy_budget < 1.0),
            )
            if active
        ]
        total_compute = sum(m.module.profile.compute_cost for m in all_selected)
        total_time = sum(m.module.profile.time_cost_ms for m in all_selected)
        total_energy = sum(m.module.profile.energy_cost for m in all_selected)
        context.metrics["constraint_violation"] = any(
            (
                total_compute > context.compute_budget,
                total_time > context.time_budget_ms,
                total_energy > energy_budget,
            )
        )

        return ExecutionPlan(modules=selected_modules)

    @staticmethod
    def _energy_budget(battery_level: float) -> float:
        if battery_level < 0.10:
            return 0.2
        if battery_level < 0.30:
            return 0.5
        return 1.0


class RiskAwareKnapsackSchedulingPolicy(SchedulingPolicy):
    def __init__(
        self,
        scoring_strategy: CriticalityScoringStrategy | None = None,
        selection_strategy: ModuleSelectionStrategy | None = None,
    ) -> None:
        self.scoring_strategy = scoring_strategy or RiskAwareCriticalityScoringStrategy()
        self.selection_strategy = selection_strategy or KnapsackSelectionStrategy()

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
        scores_by_name = {
            module.name: score for module, score in scored_modules
        }
        context.scheduler_mode = self._resolve_mode(state, context, events)
        context.is_emergency = context.scheduler_mode == "emergency"
        context.metrics["policy"] = "risk_aware_knapsack"
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
        plan = self.selection_strategy.select(
            modules,
            scores_by_name,
            state,
            context,
        )
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


class RiskAwareCriticalityScoringStrategy(CriticalityScoringStrategy):
    def __init__(
        self,
        weights: CriticalityWeights | None = None,
        resource_weights: ResourcePenaltyWeights | None = None,
    ) -> None:
        self.weights = weights or CriticalityWeights()
        self.resource_weights = resource_weights or ResourcePenaltyWeights()

    def score(
        self,
        module: Module,
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> CriticalityScore:
        safety_factor = self._compute_safety_factor(module, state, context, events)
        mission_factor = self._compute_mission_factor(module, state)
        urgency_factor = self._compute_urgency_factor(module, state, events)
        resource_penalty = self._compute_resource_penalty(module, state, context)

        raw_score = (
            (self.weights.safety * safety_factor)
            + (self.weights.mission * mission_factor)
            + (self.weights.urgency * urgency_factor)
            - (self.weights.resource_penalty * resource_penalty)
        )

        mandatory = (
            safety_factor >= 1.0
            or module.profile.is_safety_critical
            or (
                context.is_emergency
                and (module.profile.is_safety_critical or module.profile.is_diagnostic)
            )
        )

        return CriticalityScore(
            value=max(-1.0, min(1.0, raw_score)),
            safety_factor=safety_factor,
            mission_factor=mission_factor,
            urgency_factor=urgency_factor,
            resource_penalty=resource_penalty,
            mandatory=mandatory,
        )

    def _compute_safety_factor(
        self,
        module: Module,
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> float:
        factor = module.profile.safety_weight
        if context.is_emergency:
            if module.profile.is_safety_critical or module.profile.is_diagnostic:
                return 1.0
            return min(1.0, factor)

        if state.flags.get("obstacle_detected") and module.profile.is_safety_critical:
            factor += 0.5
        if state.flags.get("hardware_fault") and module.profile.is_diagnostic:
            factor += 0.6
        if state.flags.get("sensor_failure") and (
            module.profile.is_diagnostic or module.profile.is_localization
        ):
            factor += 0.5

        for event in events:
            if event.event_type.name == "SYSTEM_EMERGENCY":
                if module.profile.is_safety_critical or module.profile.is_diagnostic:
                    return 1.0
            if (
                event.event_type.name == "MODULE_FAILED"
                and module.profile.is_diagnostic
            ):
                factor += 0.4

        return min(1.0, factor)

    def _compute_mission_factor(self, module: Module, state: RobotState) -> float:
        if not module.profile.mission_tags:
            return min(1.0, module.profile.mission_weight)

        mission_status = state.mission_status.lower()
        if mission_status in module.profile.mission_tags:
            multiplier = 1.0
        elif mission_status == "active" and "active" in module.profile.mission_tags:
            multiplier = 1.0
        elif mission_status == "idle":
            multiplier = 0.0
        else:
            multiplier = 0.0
        return min(1.0, module.profile.mission_weight * multiplier)

    def _compute_urgency_factor(
        self,
        module: Module,
        state: RobotState,
        events: List[Event],
    ) -> float:
        factor = module.profile.urgency_weight
        if state.battery_level < 0.10 and (
            module.profile.is_safety_critical or module.profile.is_diagnostic
        ):
            factor += 0.3
        if state.flags.get("sensor_failure") and module.profile.is_diagnostic:
            factor += 0.4
        for event in events:
            if event.event_type.name == "SYSTEM_EMERGENCY":
                factor += 0.6
            elif (
                event.event_type.name == "DIAGNOSTIC"
                and state.flags.get("obstacle_detected")
                and module.profile.is_safety_critical
            ):
                factor += 0.2
        return min(1.0, factor)

    def _compute_resource_penalty(
        self,
        module: Module,
        state: RobotState,
        context: RuntimeContext,
    ) -> float:
        compute_budget = max(context.compute_budget, 1e-6)
        time_budget = max(context.time_budget_ms, 1e-6)
        battery_level = max(state.battery_level, 1e-6)
        profile = module.profile

        penalty = (
            self.resource_weights.compute * (profile.compute_cost / compute_budget)
            + self.resource_weights.time * (profile.time_cost_ms / time_budget)
            + self.resource_weights.energy * (profile.energy_cost / battery_level)
        )
        return min(1.0, penalty)