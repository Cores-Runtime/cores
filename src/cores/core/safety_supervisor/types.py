from __future__ import annotations

from enum import StrEnum
from dataclasses import dataclass


class SafetyDecision(StrEnum):
    ALLOW = "allow"
    PAUSE = "pause"
    CANCEL_MISSION = "cancel_mission"
    EMERGENCY_STOP = "emergency_stop"


class SafetyReason(StrEnum):
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"
    COLLISION_RISK = "collision_risk"
    HUMAN_DETECTED = "human_detected"
    TEMPERATURE_HIGH = "temperature_high"
    TEMPERATURE_CRITICAL = "temperature_critical"
    SENSOR_DEGRADED = "sensor_degraded"
    SENSOR_FAILED = "sensor_failed"


@dataclass(frozen=True)
class SafetyPolicyResult:
    decision: SafetyDecision
    reason: SafetyReason
    policy_name: str


@dataclass(frozen=True)
class SafetyResult:
    decision: SafetyDecision
    reason: SafetyReason
    triggering_policy: str
