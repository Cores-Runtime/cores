from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import StrEnum

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.events.event import Event
from cores.events.event_type import EventType


class ScenarioType(StrEnum):
    NOMINAL = "nominal"
    LOW_BATTERY = "low_battery"
    OBSTACLE = "obstacle"
    EMERGENCY = "emergency"
    BUDGET_EXHAUSTION = "budget_exhaustion"
    SENSOR_FAILURE = "sensor_failure"
    HIGH_TEMPERATURE = "high_temperature"
    COMMUNICATION_LOSS = "communication_loss"
    NAVIGATION_LOSS = "navigation_loss"
    CAMERA_DEGRADED = "camera_degraded"
    GPS_DRIFT = "gps_drift"
    LIDAR_FAILURE = "lidar_failure"
    DEADLINE_OVERLOAD = "deadline_overload"
    MEMORY_PRESSURE = "memory_pressure"
    MULTI_SENSOR_FAILURE = "multi_sensor_failure"
    THERMAL_THROTTLING = "thermal_throttling"
    NETWORK_PARTITION = "network_partition"
    ACTUATOR_DEGRADATION = "actuator_degradation"
    MISSION_CHANGE = "mission_change"
    UNKNOWN_ENVIRONMENT = "unknown_environment"


@dataclass(frozen=True)
class GeneratedScenario:
    name: str
    state: RobotState
    context: RuntimeContext
    events: List[Event]
    required_modules: List[str]
    scenario_type: ScenarioType
    severity: float
    tags: List[str] = field(default_factory=list)


def _make_robot_state(
    battery_level: float = 1.0,
    mission_status: str = "explore",
    temperature: float = 25.0,
    cpu_usage: float = 0.3,
    comm_quality: float = 1.0,
    flags: Optional[Dict] = None,
    sensor_summaries: Optional[Dict] = None,
) -> RobotState:
    return RobotState(
        battery_level=battery_level,
        mission_status=mission_status,
        temperature=temperature,
        cpu_usage=cpu_usage,
        comm_quality=comm_quality,
        flags=flags or {},
        sensor_summaries=sensor_summaries or {},
    )


def _make_runtime_context(
    compute_budget: float = 1.0,
    time_budget_ms: float = 100.0,
    deadline_ms: Optional[float] = None,
) -> RuntimeContext:
    ctx = RuntimeContext(compute_budget=compute_budget, time_budget_ms=time_budget_ms)
    if deadline_ms:
        ctx.deadline_ms = deadline_ms
    return ctx


def _make_events(*event_types: EventType, sources: Optional[List[str]] = None) -> List[Event]:
    sources = sources or ["system"] * len(event_types)
    return [Event(source=src, event_type=et) for src, et in zip(sources, event_types)]


SCENARIO_TEMPLATES = [
    {
        "type": ScenarioType.NOMINAL,
        "name": "Nominal Exploration",
        "params": {
            "battery_level": (0.7, 1.0),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.2, 0.4),
            "compute_budget": (0.8, 1.0),
            "time_budget_ms": (80.0, 120.0),
        },
        "required": ["safety_monitor"],
        "severity": 0.0,
        "tags": ["nominal"],
    },
    {
        "type": ScenarioType.LOW_BATTERY,
        "name": "Low Battery",
        "params": {
            "battery_level": (0.05, 0.15),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.2, 0.4),
            "compute_budget": (0.8, 1.0),
            "time_budget_ms": (80.0, 120.0),
        },
        "required": ["safety_monitor", "battery_monitor"],
        "severity": 0.7,
        "tags": ["power"],
    },
    {
        "type": ScenarioType.OBSTACLE,
        "name": "Obstacle Detected",
        "params": {
            "battery_level": (0.5, 0.9),
            "temperature": (20.0, 35.0),
            "cpu_usage": (0.3, 0.6),
            "compute_budget": (0.6, 1.0),
            "time_budget_ms": (40.0, 80.0),
        },
        "required": ["safety_monitor", "collision_avoidance"],
        "flags": {"obstacle_detected": True},
        "severity": 0.5,
        "tags": ["safety", "dynamic"],
    },
    {
        "type": ScenarioType.EMERGENCY,
        "name": "Emergency Event",
        "params": {
            "battery_level": (0.3, 0.7),
            "temperature": (20.0, 40.0),
            "cpu_usage": (0.4, 0.8),
            "compute_budget": (0.8, 1.0),
            "time_budget_ms": (80.0, 120.0),
        },
        "required": ["safety_monitor", "diagnostics"],
        "events": [EventType.SYSTEM_EMERGENCY],
        "severity": 1.0,
        "tags": ["emergency"],
    },
    {
        "type": ScenarioType.BUDGET_EXHAUSTION,
        "name": "Budget Exhaustion",
        "params": {
            "battery_level": (0.4, 0.8),
            "temperature": (25.0, 40.0),
            "cpu_usage": (0.7, 0.95),
            "compute_budget": (0.1, 0.4),
            "time_budget_ms": (15.0, 30.0),
        },
        "required": ["safety_monitor"],
        "severity": 0.8,
        "tags": ["resource"],
    },
    {
        "type": ScenarioType.SENSOR_FAILURE,
        "name": "Sensor Failure",
        "params": {
            "battery_level": (0.4, 0.8),
            "temperature": (20.0, 35.0),
            "cpu_usage": (0.4, 0.7),
            "compute_budget": (0.4, 0.7),
            "time_budget_ms": (30.0, 60.0),
        },
        "required": ["diagnostics", "localization"],
        "flags": {"sensor_failure": True, "hardware_fault": True},
        "sensor_summaries": {"gps": "offline", "camera": "degraded"},
        "events": [EventType.MODULE_FAILED],
        "event_sources": ["gps"],
        "severity": 0.7,
        "tags": ["sensor", "hardware"],
    },
    {
        "type": ScenarioType.HIGH_TEMPERATURE,
        "name": "High Temperature",
        "params": {
            "battery_level": (0.5, 0.9),
            "temperature": (45.0, 65.0),
            "cpu_usage": (0.5, 0.8),
            "compute_budget": (0.5, 0.8),
            "time_budget_ms": (50.0, 80.0),
        },
        "required": ["safety_monitor", "battery_monitor"],
        "flags": {"thermal_warning": True},
        "severity": 0.6,
        "tags": ["thermal"],
    },
    {
        "type": ScenarioType.COMMUNICATION_LOSS,
        "name": "Communication Loss",
        "params": {
            "battery_level": (0.4, 0.8),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.3, 0.5),
            "comm_quality": (0.0, 0.3),
            "compute_budget": (0.6, 0.9),
            "time_budget_ms": (60.0, 100.0),
        },
        "required": ["diagnostics", "logger"],
        "flags": {"comm_lost": True},
        "severity": 0.6,
        "tags": ["communication"],
    },
    {
        "type": ScenarioType.NAVIGATION_LOSS,
        "name": "Navigation Loss",
        "params": {
            "battery_level": (0.5, 0.8),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.4, 0.6),
            "compute_budget": (0.5, 0.8),
            "time_budget_ms": (40.0, 70.0),
        },
        "required": ["localization", "diagnostics", "safety_monitor"],
        "flags": {"navigation_lost": True, "gps_denied": True},
        "sensor_summaries": {"gps": "denied", "imu": "degraded"},
        "severity": 0.8,
        "tags": ["navigation", "localization"],
    },
    {
        "type": ScenarioType.CAMERA_DEGRADED,
        "name": "Camera Degraded",
        "params": {
            "battery_level": (0.5, 0.9),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.3, 0.5),
            "compute_budget": (0.6, 0.9),
            "time_budget_ms": (50.0, 80.0),
        },
        "required": ["diagnostics", "localization", "safety_monitor"],
        "flags": {"camera_degraded": True},
        "sensor_summaries": {"camera": "degraded", "lidar": "nominal"},
        "severity": 0.4,
        "tags": ["sensor", "perception"],
    },
    {
        "type": ScenarioType.GPS_DRIFT,
        "name": "GPS Drift",
        "params": {
            "battery_level": (0.5, 0.8),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.3, 0.5),
            "compute_budget": (0.6, 0.9),
            "time_budget_ms": (50.0, 80.0),
        },
        "required": ["localization", "diagnostics"],
        "flags": {"gps_drift": True},
        "sensor_summaries": {"gps": "drifting"},
        "severity": 0.5,
        "tags": ["navigation", "sensor"],
    },
    {
        "type": ScenarioType.LIDAR_FAILURE,
        "name": "LIDAR Failure",
        "params": {
            "battery_level": (0.4, 0.7),
            "temperature": (20.0, 35.0),
            "cpu_usage": (0.4, 0.6),
            "compute_budget": (0.5, 0.8),
            "time_budget_ms": (40.0, 70.0),
        },
        "required": ["collision_avoidance", "diagnostics"],
        "flags": {"lidar_failure": True},
        "sensor_summaries": {"lidar": "offline"},
        "severity": 0.7,
        "tags": ["sensor", "perception"],
    },
    {
        "type": ScenarioType.DEADLINE_OVERLOAD,
        "name": "Deadline Overload",
        "params": {
            "battery_level": (0.5, 0.8),
            "temperature": (25.0, 40.0),
            "cpu_usage": (0.8, 0.95),
            "compute_budget": (0.3, 0.6),
            "time_budget_ms": (20.0, 40.0),
        },
        "required": ["safety_monitor", "diagnostics"],
        "flags": {"deadline_miss": True},
        "severity": 0.8,
        "tags": ["timing", "resource"],
    },
    {
        "type": ScenarioType.MEMORY_PRESSURE,
        "name": "Memory Pressure",
        "params": {
            "battery_level": (0.5, 0.8),
            "temperature": (30.0, 45.0),
            "cpu_usage": (0.6, 0.8),
            "compute_budget": (0.4, 0.7),
            "time_budget_ms": (30.0, 50.0),
        },
        "required": ["safety_monitor", "diagnostics", "logger"],
        "flags": {"memory_pressure": True},
        "severity": 0.6,
        "tags": ["resource", "memory"],
    },
    {
        "type": ScenarioType.MULTI_SENSOR_FAILURE,
        "name": "Multi-Sensor Failure",
        "params": {
            "battery_level": (0.3, 0.6),
            "temperature": (20.0, 35.0),
            "cpu_usage": (0.5, 0.8),
            "compute_budget": (0.4, 0.7),
            "time_budget_ms": (30.0, 50.0),
        },
        "required": ["diagnostics", "localization", "collision_avoidance", "safety_monitor"],
        "flags": {"sensor_failure": True, "multi_sensor_fault": True},
        "sensor_summaries": {"gps": "offline", "camera": "offline", "lidar": "degraded"},
        "events": [EventType.MODULE_FAILED, EventType.DIAGNOSTIC],
        "event_sources": ["gps", "camera"],
        "severity": 0.9,
        "tags": ["sensor", "hardware", "multi"],
    },
    {
        "type": ScenarioType.THERMAL_THROTTLING,
        "name": "Thermal Throttling",
        "params": {
            "battery_level": (0.4, 0.7),
            "temperature": (60.0, 80.0),
            "cpu_usage": (0.6, 0.9),
            "compute_budget": (0.3, 0.6),
            "time_budget_ms": (20.0, 40.0),
        },
        "required": ["safety_monitor", "battery_monitor", "diagnostics"],
        "flags": {"thermal_throttling": True, "cpu_throttled": True},
        "severity": 0.8,
        "tags": ["thermal", "cpu"],
    },
    {
        "type": ScenarioType.NETWORK_PARTITION,
        "name": "Network Partition",
        "params": {
            "battery_level": (0.5, 0.8),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.3, 0.5),
            "comm_quality": (0.0, 0.2),
            "compute_budget": (0.6, 0.9),
            "time_budget_ms": (50.0, 80.0),
        },
        "required": ["diagnostics", "logger", "safety_monitor"],
        "flags": {"network_partition": True, "comm_degraded": True},
        "severity": 0.6,
        "tags": ["communication", "network"],
    },
    {
        "type": ScenarioType.ACTUATOR_DEGRADATION,
        "name": "Actuator Degradation",
        "params": {
            "battery_level": (0.5, 0.8),
            "temperature": (20.0, 35.0),
            "cpu_usage": (0.4, 0.6),
            "compute_budget": (0.5, 0.8),
            "time_budget_ms": (40.0, 70.0),
        },
        "required": ["collision_avoidance", "diagnostics", "recovery", "safety_monitor"],
        "flags": {"actuator_degraded": True, "motor_fault": True},
        "severity": 0.7,
        "tags": ["actuator", "hardware"],
    },
    {
        "type": ScenarioType.MISSION_CHANGE,
        "name": "Mission Change",
        "params": {
            "battery_level": (0.6, 0.9),
            "temperature": (20.0, 30.0),
            "cpu_usage": (0.3, 0.5),
            "compute_budget": (0.7, 1.0),
            "time_budget_ms": (60.0, 100.0),
        },
        "required": ["safety_monitor", "navigator"],
        "flags": {"mission_changed": True, "new_waypoint": True},
        "severity": 0.3,
        "tags": ["mission", "planning"],
    },
    {
        "type": ScenarioType.UNKNOWN_ENVIRONMENT,
        "name": "Unknown Environment",
        "params": {
            "battery_level": (0.5, 0.8),
            "temperature": (20.0, 35.0),
            "cpu_usage": (0.4, 0.7),
            "compute_budget": (0.5, 0.8),
            "time_budget_ms": (40.0, 70.0),
        },
        "required": ["explorer", "mapper", "localization", "safety_monitor", "diagnostics"],
        "flags": {"unknown_terrain": True, "mapping_required": True},
        "sensor_summaries": {"camera": "nominal", "lidar": "nominal", "gps": "nominal"},
        "severity": 0.5,
        "tags": ["exploration", "mapping"],
    },
]


def generate_scenario_suite(
    num_scenarios: int = 50,
    seed: int = 42,
    scenario_types: Optional[List[ScenarioType]] = None,
) -> List[GeneratedScenario]:
    rng = random.Random(seed)
    
    if scenario_types is None:
        templates = SCENARIO_TEMPLATES
    else:
        templates = [t for t in SCENARIO_TEMPLATES if t["type"] in scenario_types]
    
    scenarios = []
    
    for i in range(num_scenarios):
        template = rng.choice(templates)
        
        params = {}
        for key, (low, high) in template["params"].items():
            params[key] = rng.uniform(low, high)
        
        state = _make_robot_state(
            battery_level=params.get("battery_level", 1.0),
            mission_status="explore",
            temperature=params.get("temperature", 25.0),
            cpu_usage=params.get("cpu_usage", 0.3),
            comm_quality=params.get("comm_quality", 1.0),
            flags=template.get("flags", {}).copy(),
            sensor_summaries=template.get("sensor_summaries", {}).copy(),
        )
        
        context = _make_runtime_context(
            compute_budget=params.get("compute_budget", 1.0),
            time_budget_ms=params.get("time_budget_ms", 100.0),
            deadline_ms=params.get("deadline_ms"),
        )
        
        events = []
        for j, et in enumerate(template.get("events", [])):
            source = template.get("event_sources", ["system"])[j] if j < len(template.get("event_sources", ["system"])) else "system"
            events.append(Event(source=source, event_type=et))
        
        name = f"{template['name']} #{i+1:03d}"
        
        scenarios.append(GeneratedScenario(
            name=name,
            state=state,
            context=context,
            events=events,
            required_modules=template["required"],
            scenario_type=template["type"],
            severity=template["severity"],
            tags=template["tags"],
        ))
    
    return scenarios


def generate_stress_scenarios(seed: int = 12345) -> List[GeneratedScenario]:
    rng = random.Random(seed)
    
    stress_configs = [
        {"battery": 0.05, "temp": 70, "cpu": 0.95, "compute": 0.1, "time": 10},
        {"battery": 0.1, "temp": 65, "cpu": 0.9, "compute": 0.15, "time": 15},
        {"battery": 0.05, "temp": 50, "cpu": 0.8, "compute": 0.2, "time": 20},
        {"battery": 0.2, "temp": 40, "cpu": 0.7, "compute": 0.3, "time": 30},
    ]
    
    scenarios = []
    for i, cfg in enumerate(stress_configs):
        state = _make_robot_state(
            battery_level=cfg["battery"],
            temperature=cfg["temp"],
            cpu_usage=cfg["cpu"],
            flags={"thermal_throttling": True, "battery_critical": True, "cpu_saturated": True},
        )
        context = _make_runtime_context(
            compute_budget=cfg["compute"],
            time_budget_ms=cfg["time"],
        )
        events = [Event(source="system", event_type=EventType.SYSTEM_EMERGENCY)]
        
        scenarios.append(GeneratedScenario(
            name=f"Stress Test #{i+1}",
            state=state,
            context=context,
            events=events,
            required_modules=["safety_monitor", "battery_monitor", "diagnostics", "collision_avoidance"],
            scenario_type=ScenarioType.EMERGENCY,
            severity=1.0,
            tags=["stress", "extreme"],
        ))
    
    return scenarios