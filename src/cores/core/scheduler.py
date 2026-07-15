from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Dict, List

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_plan import ExecutionPlan
from cores.interfaces.module import Module
from cores.events.event import Event
from cores.events.event_type import EventType


@dataclass(frozen=True)
class CriticalityWeights:
    """
    Tunable criticality weights.

    The defaults are hand-tuned initial values and may be recalibrated using
    benchmarks or future optimization work.
    """

    safety: float = 0.35
    mission: float = 0.30
    urgency: float = 0.20
    resource_penalty: float = 0.15


@dataclass(frozen=True)
class ResourcePenaltyWeights:
    """
    Relative weighting of compute, time, and energy penalties.
    """

    compute: float = 0.4
    time: float = 0.3
    energy: float = 0.3


@dataclass(frozen=True)
class CriticalityScore:
    """
    Explainable criticality score decomposition for one module.
    """

    value: float
    safety_factor: float
    mission_factor: float
    urgency_factor: float
    resource_penalty: float
    mandatory: bool


class CriticalityScoringStrategy(ABC):
    """
    Strategy interface for computing module criticality.
    """

    @abstractmethod
    def score(
        self,
        module: Module,
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> CriticalityScore:
        """
        Compute a score for one module under the current runtime inputs.
        """


class DefaultCriticalityScoringStrategy(CriticalityScoringStrategy):
    """
    Deterministic criticality scoring using module descriptors and runtime state.
    """

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
            if event.event_type is EventType.SYSTEM_EMERGENCY:
                if module.profile.is_safety_critical or module.profile.is_diagnostic:
                    return 1.0
            if (
                event.event_type is EventType.MODULE_FAILED
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
            if event.event_type is EventType.SYSTEM_EMERGENCY:
                factor += 0.6
            elif (
                event.event_type is EventType.DIAGNOSTIC
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


class ModuleSelectionStrategy(ABC):
    """
    Strategy interface for turning scored modules into an execution plan.
    """

    @abstractmethod
    def select(
        self,
        modules: List[Module],
        scores: Dict[str, CriticalityScore],
        state: RobotState,
        context: RuntimeContext,
    ) -> ExecutionPlan:
        """
        Select an ordered execution plan using precomputed scores.
        """


class GreedySelectionStrategy(ModuleSelectionStrategy):
    """
    Stable greedy selection constrained by compute, time, and energy budgets.
    """

    def select(
        self,
        modules: List[Module],
        scores: Dict[str, CriticalityScore],
        state: RobotState,
        context: RuntimeContext,
    ) -> ExecutionPlan:
        energy_budget = self._energy_budget(state.battery_level)
        total_compute = 0.0
        total_time = 0.0
        total_energy = 0.0
        selected: List[Module] = []

        for module in modules:
            profile = module.profile
            score = scores[module.name]
            next_compute = total_compute + profile.compute_cost
            next_time = total_time + profile.time_cost_ms
            next_energy = total_energy + profile.energy_cost
            fits_budget = (
                next_compute <= context.compute_budget
                and next_time <= context.time_budget_ms
                and next_energy <= energy_budget
            )

            if score.mandatory or (score.value > 0.0 and fits_budget):
                selected.append(module)
                total_compute = next_compute
                total_time = next_time
                total_energy = next_energy

        context.metrics["selected"] = [module.name for module in selected]
        context.metrics["deferred"] = [
            module.name for module in modules if module.name not in context.metrics["selected"]
        ]
        context.metrics["resource_usage"] = {
            "compute": total_compute,
            "time_ms": total_time,
            "energy": total_energy,
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
        context.metrics["constraint_violation"] = any(
            (
                total_compute > context.compute_budget,
                total_time > context.time_budget_ms,
                total_energy > energy_budget,
            )
        )
        return ExecutionPlan(modules=selected)

    @staticmethod
    def _energy_budget(battery_level: float) -> float:
        if battery_level < 0.10:
            return 0.2
        if battery_level < 0.30:
            return 0.5
        return 1.0


class SchedulingPolicy(ABC):
    """
    Abstract base class for all scheduling policies in CORES.
    """

    @abstractmethod
    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        """
        Produce an ExecutionPlan based on available modules, robot state, context, and events.
        """
        pass


class DefaultSchedulingPolicy(SchedulingPolicy):
    """
    Default scheduling policy that executes all registered modules in their registered order.
    """

    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        # In Phase 1, the default policy simply schedules all registered modules in order.
        return ExecutionPlan(modules=modules.copy())


class OperatorSchedulingPolicy(SchedulingPolicy):
    """
    Baseline Operator scheduling policy.

    Orders modules by priority (higher first). Modules with equal priority
    retain their registration order. No optimization algorithms.
    """

    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        sorted_modules = sorted(
            modules,
            key=lambda module: module.priority,
            reverse=True,
        )
        return ExecutionPlan(modules=sorted_modules)


class CriticalitySchedulingPolicy(SchedulingPolicy):
    """
    Adaptive scheduling policy based on configurable criticality scoring.
    """

    def __init__(
        self,
        scoring_strategy: CriticalityScoringStrategy | None = None,
        selection_strategy: ModuleSelectionStrategy | None = None,
    ) -> None:
        self.scoring_strategy = scoring_strategy or DefaultCriticalityScoringStrategy()
        self.selection_strategy = selection_strategy or GreedySelectionStrategy()

    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        started_at = perf_counter()
        scored_modules = [
            (module, self.scoring_strategy.score(module, state, context, events))
            for module in modules
        ]
        ordered_modules = [
            module
            for module, _score in sorted(
                scored_modules,
                key=lambda item: item[1].value,
                reverse=True,
            )
        ]
        scores_by_name = {
            module.name: score for module, score in scored_modules
        }
        context.scheduler_mode = self._resolve_mode(state, context, events)
        context.is_emergency = context.scheduler_mode == "emergency"
        context.metrics["policy"] = "criticality"
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
            ordered_modules,
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
        if context.is_emergency or any(
            event.event_type is EventType.SYSTEM_EMERGENCY for event in events
        ):
            return "emergency"
        if state.battery_level < 0.30:
            return "low_power"
        return "default"


class Scheduler:
    """
    Scheduler decides which cognitive modules execute next using a SchedulingPolicy.

    It operates as a pure coordinator, delegating the planning decision to its
    configured SchedulingPolicy. It does not maintain event queues or execution state.
    """

    def __init__(self, policy: SchedulingPolicy) -> None:
        self.policy = policy

    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        """
        Generate an execution schedule based on inputs and the active policy.
        """
        return self.policy.schedule(modules, state, context, events)
