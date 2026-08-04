from __future__ import annotations

from typing import Any, Dict, List, Optional
from time import perf_counter

from cores.core.robot_state import RobotState
from cores.core.planning.types import PlanCandidate, PlanningResult, PlanningMetrics
from cores.core.planning.mission import Mission
from cores.core.planning.interface import PlanningContext, PlannerStrategy
from cores.core.planning.policy import MemoryInfluencePolicy, LinearInfluencePolicy
from cores.core.memory import (
    Memory,
    MemoryRecord,
    MemoryType,
    make_record_id,
)
from cores.core.memory.evidence import EvidenceSet


class MemoryAwarePlanner(PlannerStrategy):
    """Wraps any PlannerStrategy and biases its decisions with memory evidence.

    Cognitive loop:
        Mission -> Memory.evidence() -> Planner -> adjusted Plan -> Memory(PLAN).

    The wrapper only ever sees EvidenceSet, never raw MemoryRecords. Score
    adjustments are delegated to a MemoryInfluencePolicy, so no magic constants
    live here. With an empty memory the wrapper reduces to the base planner.
    """

    def __init__(
        self,
        base: PlannerStrategy,
        policy: Optional[MemoryInfluencePolicy] = None,
        memory: Optional[Memory] = None,
    ) -> None:
        self._base = base
        self._policy = policy or LinearInfluencePolicy()
        self._memory = memory

    @property
    def base(self) -> PlannerStrategy:
        return self._base

    @property
    def policy(self) -> MemoryInfluencePolicy:
        return self._policy

    @property
    def name(self) -> str:
        return f"memory_aware:{self._base.name}"

    def _resolve_memory(self, context: PlanningContext) -> Optional[Memory]:
        if context.memory is not None:
            return context.memory
        return self._memory

    def _gather_evidence(
        self, memory: Optional[Memory], context: PlanningContext
    ) -> EvidenceSet:
        evidence = memory.evidence() if memory is not None else EvidenceSet()
        context.metadata["memory_evidence"] = evidence
        return evidence

    def plan(
        self, state: RobotState, mission: Mission, context: PlanningContext
    ) -> PlanningResult:
        start = perf_counter()
        memory = self._resolve_memory(context)
        evidence = self._gather_evidence(memory, context)
        result = self._base.plan(state, mission, context)
        adjusted = self._apply_evidence(result, evidence)
        self._store_plan(adjusted.selected, memory, context)
        return self._build_result(adjusted, elapsed_seconds=perf_counter() - start)

    def replan(
        self,
        state: RobotState,
        mission: Mission,
        context: PlanningContext,
        previous_plan: PlanCandidate,
        changes: Dict[str, Any],
    ) -> Optional[PlanningResult]:
        start = perf_counter()
        memory = self._resolve_memory(context)
        evidence = self._gather_evidence(memory, context)
        base_result = self._base.replan(state, mission, context, previous_plan, changes)
        if base_result is None:
            base_result = self._base.plan(state, mission, context)
        adjusted = self._apply_evidence(base_result, evidence)
        self._store_plan(adjusted.selected, memory, context)
        return self._build_result(adjusted, elapsed_seconds=perf_counter() - start)

    def _apply_evidence(
        self, result: PlanningResult, evidence: EvidenceSet
    ) -> PlanningResult:
        adjusted: List[PlanCandidate] = []
        for cand in result.candidates:
            failures, successes = 0, 0
            for action in cand.actions:
                f = evidence.failure_count(action.name)
                if f == 0:
                    f = evidence.failure_count(action.action_id)
                failures += f
                s = evidence.success_count(action.name)
                if s == 0:
                    s = evidence.success_count(action.action_id)
                successes += s
            adjusted.append(
                PlanCandidate(
                    plan_id=cand.plan_id,
                    goal_id=cand.goal_id,
                    actions=list(cand.actions),
                    confidence=self._policy.adjust_confidence(
                        cand.confidence, failures, successes
                    ),
                    estimated_cost=cand.estimated_cost,
                    estimated_duration_cycles=cand.estimated_duration_cycles,
                    utility=self._policy.adjust_utility(cand.utility, failures, successes),
                    metadata={**cand.metadata, "memory_adjusted": True},
                )
            )
        adjusted.sort(key=lambda c: c.utility, reverse=True)
        selected = adjusted[0] if adjusted else None
        return PlanningResult(
            candidates=adjusted,
            selected=selected,
            metrics=result.metrics,
            context=result.context,
        )

    def _store_plan(
        self,
        selected: Optional[PlanCandidate],
        memory: Optional[Memory],
        context: PlanningContext,
    ) -> None:
        if selected is None or memory is None:
            return
        content = {
            "plan_id": selected.plan_id,
            "goal_id": selected.goal_id,
            "actions": [a.name for a in selected.actions],
            "utility": selected.utility,
            "cycle": context.cycle_count,
        }
        memory.store(
            MemoryRecord(
                id=make_record_id(content, context.cycle_count),
                content=content,
                cycle=context.cycle_count,
                importance=max(0.5, selected.utility),
                record_type=MemoryType.PLAN,
            )
        )

    def _build_result(
        self, result: PlanningResult, elapsed_seconds: float
    ) -> PlanningResult:
        metrics = PlanningMetrics(
            planning_latency_ms=elapsed_seconds * 1000,
            candidates_generated=result.metrics.candidates_generated,
            goals_considered=result.metrics.goals_considered,
            replanning_triggered=result.metrics.replanning_triggered,
            strategy_name=self.name,
        )
        return PlanningResult(
            candidates=result.candidates,
            selected=result.selected,
            metrics=metrics,
            context={**result.context, "memory_aware": True},
        )
