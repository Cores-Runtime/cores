from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.events.event import Event
from cores.events.event_type import EventType
from cores.interfaces.module import Module, ModuleResult
from cores.runtime.runtime_state import (
    RuntimeState,
    MissionState,
    ModuleState,
    SchedulerState,
    RobotSnapshot,
    EventsSnapshot,
    ExplainabilityState,
    WorldModelSnapshot,
    EnvironmentSnapshot,
    DetectedObjectSnapshot,
    UncertaintySnapshot,
)


class RuntimeBridge(ABC):
    @abstractmethod
    def publish(self, state: RuntimeState) -> None:
        pass

    @abstractmethod
    def snapshot(self) -> Optional[RuntimeState]:
        pass

    @abstractmethod
    def subscribe(self, callback: Callable[[RuntimeState], None]) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class InMemoryRuntimeBridge(RuntimeBridge):
    def __init__(self) -> None:
        self._subscribers: List[Callable[[RuntimeState], None]] = []
        self._latest_snapshot: Optional[RuntimeState] = None
        self._all_snapshots: List[RuntimeState] = []

    def publish(self, state: RuntimeState) -> None:
        self._latest_snapshot = state
        self._all_snapshots.append(state)
        for callback in self._subscribers:
            callback(state)

    def snapshot(self) -> Optional[RuntimeState]:
        return self._latest_snapshot

    def subscribe(self, callback: Callable[[RuntimeState], None]) -> None:
        self._subscribers.append(callback)

    def close(self) -> None:
        self._subscribers.clear()
        self._latest_snapshot = None

    @property
    def snapshots(self) -> List[RuntimeState]:
        return list(self._all_snapshots)

    @property
    def snapshot_count(self) -> int:
        return len(self._all_snapshots)


class RuntimeStateBuilder:
    def build(
        self,
        *,
        state: RobotState,
        context: RuntimeContext,
        modules: List[Module],
        module_results: List[ModuleResult],
        cycle_events: List[Event],
        decision_time_ms: float,
        physicist: Any = None,
    ) -> RuntimeState:
        active = []
        sleeping = []
        suspended = []
        module_states = []

        for m in modules:
            ms = ModuleState(
                name=m.name,
                status="active",
                priority=m.priority,
                safety_weight=m.profile.safety_weight,
                mission_weight=m.profile.mission_weight,
                urgency_weight=m.profile.urgency_weight,
                compute_cost=m.profile.compute_cost,
                time_cost_ms=m.profile.time_cost_ms,
                energy_cost=m.profile.energy_cost,
                is_safety_critical=m.profile.is_safety_critical,
                is_diagnostic=m.profile.is_diagnostic,
                is_recovery=m.profile.is_recovery,
                is_localization=m.profile.is_localization,
            )
            module_states.append(ms)
            active.append(m.name)

        scheduler_metrics = context.metrics
        selected = scheduler_metrics.get("selected", [])
        deferred = scheduler_metrics.get("deferred", [])

        lexicographic_value = None
        lv = scheduler_metrics.get("lexicographic_value")
        if lv is not None:
            lexicographic_value = {k: float(v) for k, v in lv.items()}

        scheduler_state = SchedulerState(
            policy=scheduler_metrics.get("policy", ""),
            mode=context.scheduler_mode,
            cycle_count=context.cycle_count,
            selected_modules=list(selected),
            deferred_modules=list(deferred),
            resource_usage={
                k: float(v)
                for k, v in scheduler_metrics.get("resource_usage", {}).items()
            },
            constraints_active=list(scheduler_metrics.get("constraints_active", [])),
            constraint_violation=bool(scheduler_metrics.get("constraint_violation", False)),
            decision_time_ms=decision_time_ms,
            scores={
                name: {sk: float(sv) for sk, sv in sc.items()}
                for name, sc in scheduler_metrics.get("scores", {}).items()
            },
            lexicographic_value=lexicographic_value,
        )

        obstacles = []
        warnings = []
        recoveries = []
        cycle_event_dicts = []

        for ev in cycle_events:
            entry = {
                "event_id": ev.event_id,
                "timestamp": ev.timestamp.isoformat() if isinstance(ev.timestamp, datetime) else str(ev.timestamp),
                "source": ev.source,
                "event_type": str(ev.event_type),
                "payload": dict(ev.payload),
            }
            cycle_event_dicts.append(entry)

            if ev.event_type == EventType.SYSTEM_EMERGENCY:
                warnings.append(entry)
            elif ev.event_type == EventType.DIAGNOSTIC:
                if ev.payload.get("type") == "obstacle":
                    obstacles.append(entry)
            if ev.payload and ev.payload.get("is_recovery"):
                recoveries.append(entry)

        flags = state.flags if hasattr(state, "flags") else {}

        understanding = physicist.strategy if physicist is not None else context.world_model
        if understanding is not None:
            world_snapshot = WorldModelSnapshot(
                environment=EnvironmentSnapshot(
                    terrain=understanding.environment.terrain,
                    weather=understanding.environment.weather,
                    temperature=understanding.environment.temperature,
                    lighting=understanding.environment.lighting,
                    hazard_count=len(understanding.environment.hazards),
                    obstacle_distance=understanding.environment.obstacle_distance,
                ),
                objects=[
                    DetectedObjectSnapshot(
                        id=o.id,
                        object_type=o.object_type,
                        position=dict(o.position),
                        confidence=o.confidence,
                        last_seen_cycle=o.last_seen_cycle,
                    )
                    for o in understanding.objects
                ],
                uncertainty=UncertaintySnapshot(
                    localization=understanding.uncertainty.localization,
                    mapping=understanding.uncertainty.mapping,
                    perception=understanding.uncertainty.perception,
                    sensor_health=dict(understanding.uncertainty.sensor_health),
                ),
                obstacle_count=understanding.obstacle_count,
                last_update_cycle=understanding.last_update_cycle,
            )
        else:
            world_snapshot = WorldModelSnapshot()

        return RuntimeState(
            timestamp=datetime.now(),
            mission=MissionState(
                mission_id=state.metadata.get("mission_id", ""),
                state=state.mission_status,
                progress=state.metadata.get("progress", 0.0),
            ),
            modules=module_states,
            active_module_names=active,
            sleeping_module_names=sleeping,
            suspended_module_names=suspended,
            scheduler=scheduler_state,
            robot=RobotSnapshot(
                battery_level=state.battery_level,
                position={
                    k: float(v) for k, v in (state.pose or {}).items()
                },
                velocity={
                    k: float(v) for k, v in (state.velocity or {}).items()
                },
                flags=flags,
            ),
            events=EventsSnapshot(
                cycle_events=cycle_event_dicts,
                obstacles=obstacles,
                warnings=warnings,
                recoveries=recoveries,
            ),
            explainability=ExplainabilityState(
                scheduler_rationale=self._build_rationale(
                    scheduler_state, context, module_states
                ),
                module_changes=[physicist.last_explanation] if physicist is not None and physicist.last_explanation else [],
            ),
            world_model=world_snapshot,
        )

    @staticmethod
    def _build_rationale(
        scheduler_state: SchedulerState,
        context: RuntimeContext,
        module_states: List[ModuleState],
    ) -> str:
        parts = []
        parts.append(f"Mode: {scheduler_state.mode}")
        parts.append(f"Cycle: {scheduler_state.cycle_count}")

        reasons = []

        if scheduler_state.constraint_violation:
            reasons.append("constraint violation detected")

        active_constraints = scheduler_state.constraints_active
        if "battery" in active_constraints:
            reasons.append("tight energy budget")
        if "compute" in active_constraints:
            reasons.append("limited compute budget")
        if "time" in active_constraints:
            reasons.append("tight time budget")

        if scheduler_state.mode == "emergency":
            reasons.append("emergency mode active")
        elif scheduler_state.mode == "low_power":
            reasons.append("low power mode")

        selected = scheduler_state.selected_modules
        deferred = scheduler_state.deferred_modules
        if selected:
            reasons.append(f"selected {len(selected)} modules")
        if deferred:
            reasons.append(f"deferred {len(deferred)} modules")

        if reasons:
            parts.append("; ".join(reasons))

        return " | ".join(parts)
