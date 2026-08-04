"""Record a real runtime trace from the CORES Runtime.

Runs the actual Runtime for 120 cycles with scenario modules, a mission-aware
state estimator, the GoalPlanner, and the criticality scheduler. Every
published RuntimeState snapshot is mapped into the TraceSnapshot shape that
the homepage replay page consumes and written to:

    homepage/public/data/runtime-trace.json

Run:  uv run python scripts/record_runtime_trace.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cores.core import ExecutionLayer, Runtime, Scheduler
from cores.core.planning.goal_planner import ActionModel, GoalPlanner
from cores.core.planning.interface import Planner
from cores.core.planning.mission import Mission
from cores.core.planning.types import Goal
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.scheduler import CriticalitySchedulingPolicy
from cores.core.state_estimator import StateEstimator
from cores.events.event import Event
from cores.events.event_type import EventType
from cores.interfaces.module import Module, ModuleProfile, ModuleResult, ModuleStatus
from cores.runtime.runtime_bridge import RuntimeBridge
from cores.runtime.runtime_state import RuntimeState

N_CYCLES = 120
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "homepage"
    / "public"
    / "data"
    / "runtime-trace.json"
)

MISSION = {
    "id": "mars_rover",
    "name": "Mars Exploration",
    "desc": "Navigate rocky terrain to reach a sample site 500m away.",
    "constraints": ["Low power budget", "21-min comms delay", "Thermal cycling"],
}

DISPLAY_NAMES = {
    "mission-manager": "Mission Manager",
    "perception-engine": "Perception Engine",
    "planning-engine": "Planning Engine",
    "state-estimator": "State Estimator",
    "navigation-controller": "Navigation Controller",
    "motion-controller": "Motion Controller",
    "safety-supervisor": "Safety Supervisor",
    "telemetry-logger": "Telemetry / Logger",
    "policy-engine": "Policy Engine",
}

TRACE_EVENTS = {"Rockslide": 10, "Dust Storm": 30, "Battery Drain": 50}

METADATA = {
    "mission": MISSION,
    "robot": {
        "platform": "Rover-X2",
        "sensors": ["camera", "lidar", "gps", "imu", "thermal"],
        "actuators": ["wheel", "arm", "antenna"],
    },
    "environment": {
        "type": "Martian surface",
        "hazards": ["rocks", "dust storms", "extreme cold", "radiation"],
        "lighting": "Variable",
    },
    "scenario": {
        "id": "exploration_01",
        "category": "planetary",
        "difficulty": "hard",
    },
}


# ---------------------------------------------------------------------------
# Scenario modules
# ---------------------------------------------------------------------------


def _profile(
    *,
    safety: float = 0.0,
    mission: float = 0.0,
    urgency: float = 0.0,
    compute: float = 0.0,
    time_ms: float = 0.0,
    energy: float = 0.0,
    safety_critical: bool = False,
    diagnostic: bool = False,
    recovery: bool = False,
    localization: bool = False,
    deps: tuple[str, ...] = (),
    description: str = "",
) -> ModuleProfile:
    return ModuleProfile(
        safety_weight=safety,
        mission_weight=mission,
        urgency_weight=urgency,
        compute_cost=compute,
        time_cost_ms=time_ms,
        energy_cost=energy,
        is_safety_critical=safety_critical,
        is_diagnostic=diagnostic,
        is_recovery=recovery,
        is_localization=localization,
        dependencies=frozenset(deps),
        description=description,
    )


MODULE_SPECS: List[tuple[str, int, ModuleProfile]] = [
    (
        "mission-manager",
        1,
        _profile(
            safety=0.3,
            mission=0.9,
            compute=0.08,
            time_ms=10.0,
            energy=0.10,
            description="Mission-level decision making.",
        ),
    ),
    (
        "perception-engine",
        2,
        _profile(
            mission=0.6,
            urgency=0.5,
            compute=0.16,
            time_ms=20.0,
            energy=0.20,
            deps=("mission-manager",),
            description="Analyzes terrain and samples.",
        ),
    ),
    (
        "planning-engine",
        3,
        _profile(
            mission=0.8,
            compute=0.22,
            time_ms=30.0,
            energy=0.30,
            deps=("perception-engine",),
            description="Trajectory optimization.",
        ),
    ),
    (
        "state-estimator",
        7,
        _profile(
            safety=0.5,
            mission=0.4,
            localization=True,
            compute=0.06,
            time_ms=5.0,
            energy=0.05,
            deps=("planning-engine",),
            description="Thermal and power modeling.",
        ),
    ),
    (
        "navigation-controller",
        1,
        _profile(
            safety=0.9,
            mission=0.6,
            compute=0.05,
            time_ms=8.0,
            energy=0.06,
            deps=("mission-manager", "state-estimator"),
            description="Obstacle avoidance.",
        ),
    ),
    (
        "motion-controller",
        4,
        _profile(
            mission=0.9,
            urgency=0.4,
            compute=0.12,
            time_ms=15.0,
            energy=0.15,
            deps=("navigation-controller", "planning-engine"),
            description="Path execution.",
        ),
    ),
    (
        "safety-supervisor",
        9,
        _profile(
            safety=1.0,
            mission=0.3,
            urgency=0.8,
            safety_critical=True,
            recovery=True,
            compute=0.02,
            time_ms=3.0,
            energy=0.02,
            deps=("mission-manager",),
            description="Mission control interface.",
        ),
    ),
    (
        "telemetry-logger",
        5,
        _profile(
            compute=0.02,
            time_ms=3.0,
            energy=0.02,
            diagnostic=True,
            description="Mission logging.",
        ),
    ),
    (
        "policy-engine",
        8,
        _profile(
            safety=0.7,
            mission=0.5,
            compute=0.01,
            time_ms=2.0,
            energy=0.01,
            deps=("mission-manager", "telemetry-logger"),
            description="Ethical validation.",
        ),
    ),
]


def _no_events(state: RobotState, context: RuntimeContext) -> List[Event]:
    return []


def _navigation_events(state: RobotState, context: RuntimeContext) -> List[Event]:
    if state.flags.get("obstacle_detected"):
        return [
            Event(
                source="navigation-controller",
                event_type=EventType.DIAGNOSTIC,
                payload={"type": "obstacle", "message": "Obstacle within 0.3m", "distance": 0.3},
            )
        ]
    return []


def _safety_events(state: RobotState, context: RuntimeContext) -> List[Event]:
    if state.battery_level < 0.12:
        return [
            Event(
                source="safety-supervisor",
                event_type=EventType.SYSTEM_EMERGENCY,
                payload={"message": "Critical battery, engaging recovery", "is_recovery": True},
            )
        ]
    return []


EMITTERS: Dict[str, Callable[[RobotState, RuntimeContext], List[Event]]] = {
    "navigation-controller": _navigation_events,
    "safety-supervisor": _safety_events,
}


def scenario_events(cycle: int) -> List[Event]:
    """Environmental observations injected by the mission controller."""
    if cycle == 10:
        return [
            Event(
                source="mission-control",
                event_type=EventType.DIAGNOSTIC,
                payload={"type": "obstacle", "message": "Rockslide blocks path at 12m", "distance": 12.0},
            )
        ]
    if cycle == 30:
        return [
            Event(
                source="mission-control",
                event_type=EventType.DIAGNOSTIC,
                payload={"type": "weather", "message": "Dust storm approaching"},
            )
        ]
    if cycle == 50:
        return [
            Event(
                source="mission-control",
                event_type=EventType.DIAGNOSTIC,
                payload={"type": "power", "message": "Battery drain detected"},
            )
        ]
    return []


class ScenarioModule(Module):
    def __init__(
        self,
        name: str,
        priority: int,
        profile: ModuleProfile,
        emit: Callable[[RobotState, RuntimeContext], List[Event]],
    ) -> None:
        super().__init__(name=name, priority=priority, profile=profile)
        self._emit = emit

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(
            module_name=self.name,
            status=ModuleStatus.SUCCESS,
            events=self._emit(state, context),
            metrics={"task": self.name},
        )


# ---------------------------------------------------------------------------
# Mission state estimator
# ---------------------------------------------------------------------------


class MissionEstimator(StateEstimator):
    def estimate(self, cycle_count: int) -> RobotState:
        progress = min(1.0, cycle_count / (N_CYCLES - 5))
        x = 50.0 * progress
        y = 6.0 * math.sin(progress * math.pi * 1.6)
        dx = 50.0
        dy = 6.0 * math.pi * 1.6 * math.cos(progress * math.pi * 1.6)
        theta = math.degrees(math.atan2(dy, dx))

        battery = 1.0 - cycle_count * 0.006
        if cycle_count >= 50:
            battery -= min(cycle_count - 50, 30) * 0.01
        battery = max(0.05, battery)

        if cycle_count >= 110:
            mission_status = "complete"
        elif cycle_count >= 3:
            mission_status = "active"
        else:
            mission_status = "idle"

        return RobotState(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc)
            + timedelta(seconds=cycle_count),
            battery_level=battery,
            pose={"x": round(x, 3), "y": round(y, 3), "theta": round(theta, 3)},
            velocity={"linear": 0.5, "angular": 0.0},
            mission_status=mission_status,
            sensor_summaries={
                "lidar_points": 360,
                "imu_temperature_c": 25.0 + cycle_count * 0.1,
            },
            flags={
                "obstacle_detected": 10 <= cycle_count <= 15 or 60 <= cycle_count <= 65,
                "hardware_fault": False,
                "sensor_failure": 90 <= cycle_count <= 100,
                "sample_collected": cycle_count >= 110,
            },
            metadata={
                "source": "recorded",
                "cycle": cycle_count,
                "progress": round(progress, 4),
                "mission_id": "mars_rover",
            },
        )


# ---------------------------------------------------------------------------
# Recording bridge
# ---------------------------------------------------------------------------


class RecordingBridge(RuntimeBridge):
    def __init__(self) -> None:
        self._states: List[RuntimeState] = []

    def publish(self, state: RuntimeState) -> None:
        self._states.append(state)

    def snapshot(self) -> Optional[RuntimeState]:
        return self._states[-1] if self._states else None

    def subscribe(self, callback: Callable[[RuntimeState], None]) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def states(self) -> List[RuntimeState]:
        return list(self._states)


# ---------------------------------------------------------------------------
# Trace mapping
# ---------------------------------------------------------------------------


def _task_for(name: str, raw: RuntimeState) -> str:
    obstacle = raw.robot.flags.get("obstacle_detected", False)
    emergency = raw.scheduler.mode == "emergency"
    tasks = {
        "mission-manager": "Monitoring mission",
        "perception-engine": "Scanning terrain" if obstacle else "Standby",
        "planning-engine": "Optimizing trajectory",
        "state-estimator": "Fusing sensor data",
        "navigation-controller": "Avoiding obstacle" if obstacle else "Following path",
        "motion-controller": "Executing path",
        "safety-supervisor": "Emergency response" if emergency else "Monitoring safety",
        "telemetry-logger": "Logging telemetry",
        "policy-engine": "Validating actions",
    }
    return tasks.get(name, f"{name} task")


def build_module_defs(modules: List[Module]) -> List[dict]:
    defs = []
    for m in modules:
        defs.append(
            {
                "id": m.name,
                "name": DISPLAY_NAMES.get(m.name, m.display_name),
                "priority": m.priority,
                "cpuCost": round(m.profile.compute_cost * 100),
                "deps": sorted(m.profile.dependencies),
                "purpose": m.profile.description or f"{m.name} module",
            }
        )
    return defs


def to_trace_snapshot(raw: RuntimeState, tick: int, module_defs: List[dict]) -> dict:
    selected = raw.scheduler.selected_modules
    deferred = raw.scheduler.deferred_modules
    mode = raw.scheduler.mode
    obstacle = raw.robot.flags.get("obstacle_detected", False)
    progress = raw.mission.progress * 100.0

    modules = {}
    for m in raw.modules:
        status = (
            "running"
            if m.name in selected
            else "suspended"
            if m.name in deferred
            else "sleeping"
        )
        modules[m.name] = {
            "status": status,
            "reason": "Core" if status == "running" else "Awaiting trigger",
            "cpu": round(m.compute_cost * 100),
            "task": _task_for(m.name, raw),
            "lastActivation": tick,
            "wakeCount": 1 if status == "running" else 0,
            "totalRuntime": m.time_cost_ms,
            "recentDecisions": [],
        }

    world = {
        "obstacleDistance": 0.3 if obstacle else 10,
        "terrain": "Rocky Gravel",
        "slope": 3,
        "wheelHealth": 60 if mode == "emergency" else 100,
        "temperature": -60,
        "weather": "Dust Storm" if mode == "low_power" else "Clear",
        "commsQuality": 0.7,
        "gpsQuality": 0.9,
        "cameraQuality": 0.3 if raw.robot.flags.get("sensor_failure") else 0.95,
        "lidarQuality": 0.2 if raw.robot.flags.get("sensor_failure") else 0.9,
    }

    robot = {
        "x": raw.robot.position.get("x", 0.0),
        "y": raw.robot.position.get("y", 0.0),
        "heading": raw.robot.position.get("theta", 0.0),
        "battery": round(raw.robot.battery_level * 100.0, 2),
        "cpu": 50,
        "memory": 40,
        "missionProgress": round(progress, 2),
        "powerState": {"emergency": "Emergency", "low_power": "Low Power"}.get(
            mode, "Nominal"
        ),
    }

    decision = None
    if selected or deferred:
        decision = {
            "tick": tick,
            "reason": raw.explainability.scheduler_rationale,
            "wake": list(selected),
            "sleep": [],
            "suspend": list(deferred),
            "priority": raw.scheduler.policy or "criticality",
            "hierarchy": [f"constraint:{c}" for c in raw.scheduler.constraints_active],
            "decisionTimeMs": round(raw.scheduler.decision_time_ms, 2),
        }

    events = []
    for ev in raw.events.cycle_events:
        etype = (
            "warning"
            if ev["event_type"] in ("system_emergency", "module_failed")
            else "info"
        )
        events.append(
            {
                "tick": tick,
                "time": tick,
                "event": f"{ev['source']}: {ev['payload'].get('message', ev['event_type'])}",
                "type": etype,
            }
        )

    energy = raw.scheduler.resource_usage.get("energy", 0.0)
    metrics = {
        "battery": [round(raw.robot.battery_level * 100.0, 2)],
        "cpu": [50],
        "memory": [40],
        "latency": [round(raw.scheduler.decision_time_ms, 2)],
        "utility": [round(progress, 2)],
        "safety": [0 if mode == "emergency" else 100],
        "headroom": [round(max(0.0, 100.0 - energy * 100.0), 2)],
        "events": [len(raw.events.cycle_events)],
    }

    return {
        "tick": tick,
        "timestamp": tick,
        "status": "running",
        "mission": MISSION,
        "moduleDefs": module_defs,
        "world": world,
        "robot": robot,
        "modules": modules,
        "decision": decision,
        "eventHistory": events,
        "metrics": metrics,
        "runtimeVersion": "0.1.0",
        "schemaVersion": "1",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_runtime(
    bridge: Optional[RuntimeBridge] = None,
) -> tuple[Runtime, RuntimeBridge, List[Module]]:
    modules = [
        ScenarioModule(name, priority, profile, emit=EMITTERS.get(name, _no_events))
        for name, priority, profile in MODULE_SPECS
    ]

    scheduler = Scheduler(CriticalitySchedulingPolicy())
    estimator = MissionEstimator()
    planner = Planner(
        GoalPlanner(
            actions=[
                ActionModel(
                    "drive_forward",
                    "Drive Forward",
                    cost=1.0,
                    effects={"mission_status": "complete"},
                ),
                ActionModel(
                    "scan_terrain",
                    "Scan Terrain",
                    cost=0.5,
                    effects={"survey_complete": True},
                ),
            ]
        )
    )
    mission = Mission(
        mission_id="mars_rover",
        goals=[
            Goal(
                goal_id="reach_sample_site",
                description="Reach the sample site 500m away",
                priority=2.0,
                category="science",
                constraints={"mission_status": "complete"},
            ),
            Goal(
                goal_id="survey_region",
                description="Survey the surrounding region",
                priority=0.8,
                category="recon",
                constraints={"survey_complete": True},
            ),
        ],
    )

    if bridge is None:
        bridge = RecordingBridge()
    runtime = Runtime(
        scheduler,
        ExecutionLayer(),
        state_estimator=estimator,
        bridge=bridge,
        planner=planner,
        mission=mission,
    )
    runtime.context.compute_budget = 0.6
    runtime.context.time_budget_ms = 60.0

    for m in modules:
        runtime.register_module(m)

    return runtime, bridge, modules


def main() -> None:
    runtime, bridge, modules = build_runtime()
    module_defs = build_module_defs(modules)

    for cycle in range(N_CYCLES):
        for event in scenario_events(cycle):
            runtime.event_bus.publish(event)
        if cycle >= 110:
            runtime.mission_manager.complete_goal("reach_sample_site")
        if cycle >= 111:
            runtime.mission_manager.complete_goal("survey_region")
        runtime.step()

    snapshots = [
        to_trace_snapshot(state, tick, module_defs)
        for tick, state in enumerate(bridge.states)
    ]

    trace = {
        "version": "0.1.0",
        "schemaVersion": "1",
        "metadata": METADATA,
        "events": TRACE_EVENTS,
        "snapshots": snapshots,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(trace, fh, indent=1)

    print(f"Recorded {len(snapshots)} snapshots over {N_CYCLES} runtime cycles")
    print(f"Wrote {OUTPUT_PATH}")

    decision_ticks = sum(1 for s in snapshots if s["decision"] is not None)
    with_events = sum(1 for s in snapshots if s["eventHistory"])
    print(f"Decisions present: {decision_ticks} ticks")
    print(f"Ticks with events: {with_events}")


if __name__ == "__main__":
    main()
