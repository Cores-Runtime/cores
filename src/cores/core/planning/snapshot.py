from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from cores.core.robot_state import RobotState
from cores.core.world_model.interface import WorldModelStrategy


def _canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        items = [_canonical(v) for v in value]
        return sorted(items, key=repr)
    return value


@dataclass(frozen=True)
class PlanningSnapshotPolicy:
    """Deterministic projection rules for the planning snapshot.

    Every knob that decides what counts as a planning-relevant change lives
    here. Right now only the battery bucket is populated; later phases extend
    this object to cover temperature buckets, position quantization, sensor
    health mapping, fault inclusion, and object rounding.
    """

    battery_buckets: Tuple[Tuple[float, str], ...] = (
        (0.0, "critical"),
        (0.1, "low"),
        (0.3, "medium"),
        (0.6, "high"),
    )
    temperature_round_dp: int = 0
    position_round_dp: int = 1
    obstacle_distance_round_dp: int = 1
    sensor_health_thresholds: Tuple[Tuple[float, str], ...] = (
        (0.0, "failed"),
        (0.1, "degraded"),
        (0.5, "healthy"),
    )
    sensor_health_map: Dict[str, str] = field(
        default_factory=lambda: {
            "nominal": "healthy",
            "ok": "healthy",
            "healthy": "healthy",
            "degraded": "degraded",
            "failed": "failed",
        }
    )
    fault_flags: Tuple[str, ...] = (
        "sensor_fault",
        "navigation_fault",
        "payload_fault",
        "collision_fault",
    )

    def bucket(self, value: float, buckets: Tuple[Tuple[float, str], ...]) -> str:
        label = buckets[0][1]
        for threshold, name in buckets:
            if value >= threshold:
                label = name
        return label

    def battery_bucket(self, level: float) -> str:
        return self.bucket(level, self.battery_buckets)

    def sensor_status(self, value: Any) -> str:
        if isinstance(value, bool):
            value = 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            return self.bucket(float(value), self.sensor_health_thresholds)
        key = str(value).strip().lower()
        return self.sensor_health_map.get(key, key)


def build_planning_snapshot(
    robot: RobotState,
    world: WorldModelStrategy,
    policy: PlanningSnapshotPolicy = PlanningSnapshotPolicy(),
) -> Dict[str, Any]:
    """Project robot + world into a deterministic, canonical planning snapshot.

    Pure function: no caching, no mutable state, no timestamps. Given the same
    robot, world, and policy it always returns byte-identical output.
    """
    env = world.environment
    environment = {
        "terrain": env.terrain,
        "weather": env.weather,
        "temperature": round(env.temperature, policy.temperature_round_dp),
        "lighting": env.lighting,
        "hazards": _canonical(env.hazards),
        "obstacle_distance": round(env.obstacle_distance, policy.obstacle_distance_round_dp),
    }

    objects = []
    for obj in sorted(world.objects, key=lambda o: o.id):
        position = {
            k: round(v, policy.position_round_dp)
            for k, v in sorted(obj.position.items())
        }
        objects.append(
            {
                "id": obj.id,
                "object_type": obj.object_type,
                "position": position,
                "properties": _canonical(obj.properties),
            }
        )

    fault_flags = sorted(
        k for k, v in robot.flags.items() if v is True and k in policy.fault_flags
    )
    payload = sorted(str(p) for p in (robot.metadata.get("payload") or []))
    sensor_health = {
        k: policy.sensor_status(v)
        for k, v in sorted(robot.sensor_summaries.items())
    }

    return {
        "battery_bucket": policy.battery_bucket(robot.battery_level),
        "mission_status": robot.mission_status,
        "fault_flags": fault_flags,
        "payload": payload,
        "region": robot.metadata.get("region"),
        "waypoint": robot.metadata.get("waypoint"),
        "sensor_health": sensor_health,
        "environment": environment,
        "objects": objects,
    }


def diff_snapshots(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Return top-level key diffs between two snapshots, in sorted key order."""
    changes: Dict[str, Any] = {}
    for key in sorted(set(previous) | set(current)):
        prev = previous.get(key)
        curr = current.get(key)
        if prev != curr:
            changes[key] = {"from": prev, "to": curr}
    return changes
