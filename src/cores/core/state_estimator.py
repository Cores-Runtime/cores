from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from cores.core.robot_state import RobotState


class StateEstimator(ABC):
    """
    StateEstimator produces RobotState from available sensor data.

    During Phase 1, implementations use simulated values only.
    """

    @abstractmethod
    def estimate(self, cycle_count: int) -> RobotState:
        """
        Produce a RobotState for the given runtime cycle.

        Args:
            cycle_count: The current runtime cycle index (0-based).

        Returns:
            A RobotState representing the robot at this cycle.
        """
        pass


class SimulatedStateEstimator(StateEstimator):
    """
    Deterministic state estimator using simple simulated values.

    Produces predictable state updates suitable for simulation and benchmarking.
    No ROS2 or hardware dependencies.
    """

    _EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _BATTERY_DRAIN_PER_CYCLE = 0.01
    _POSE_STEP = 0.1

    def estimate(self, cycle_count: int) -> RobotState:
        battery = max(0.0, 1.0 - cycle_count * self._BATTERY_DRAIN_PER_CYCLE)
        mission_status = "active" if cycle_count >= 3 else "idle"

        return RobotState(
            timestamp=self._EPOCH + timedelta(seconds=cycle_count),
            battery_level=battery,
            pose={
                "x": cycle_count * self._POSE_STEP,
                "y": 0.0,
                "theta": 0.0,
            },
            velocity={"linear": 0.5, "angular": 0.0},
            mission_status=mission_status,
            sensor_summaries={
                "lidar_points": 360,
                "imu_temperature_c": 25.0 + cycle_count * 0.1,
            },
            flags={
                "obstacle_detected": cycle_count % 5 == 4,
                "hardware_fault": False,
            },
            metadata={"source": "simulated", "cycle": cycle_count},
        )
