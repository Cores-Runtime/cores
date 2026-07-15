from datetime import datetime, timedelta, timezone

import pytest

from cores.core import SimulatedStateEstimator, StateEstimator, RobotState


def test_simulated_state_estimator_produces_robot_state() -> None:
    estimator = SimulatedStateEstimator()
    state = estimator.estimate(0)

    assert isinstance(state, RobotState)
    assert state.battery_level == 1.0
    assert state.mission_status == "idle"
    assert state.pose == {"x": 0.0, "y": 0.0, "theta": 0.0}


def test_simulated_state_estimator_deterministic() -> None:
    estimator = SimulatedStateEstimator()

    state_a = estimator.estimate(7)
    state_b = estimator.estimate(7)

    assert state_a == state_b


def test_simulated_state_estimator_battery_drain() -> None:
    estimator = SimulatedStateEstimator()

    state_0 = estimator.estimate(0)
    state_10 = estimator.estimate(10)

    assert state_0.battery_level == 1.0
    assert state_10.battery_level == 0.9


def test_simulated_state_estimator_battery_floor() -> None:
    estimator = SimulatedStateEstimator()
    state = estimator.estimate(200)

    assert state.battery_level == 0.0


def test_simulated_state_estimator_pose_advances() -> None:
    estimator = SimulatedStateEstimator()

    state_3 = estimator.estimate(3)
    state_5 = estimator.estimate(5)

    assert state_3.pose["x"] == pytest.approx(0.3)
    assert state_5.pose["x"] == pytest.approx(0.5)


def test_simulated_state_estimator_mission_status_transition() -> None:
    estimator = SimulatedStateEstimator()

    assert estimator.estimate(2).mission_status == "idle"
    assert estimator.estimate(3).mission_status == "active"


def test_simulated_state_estimator_timestamp_is_deterministic() -> None:
    estimator = SimulatedStateEstimator()
    expected = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=4)

    assert estimator.estimate(4).timestamp == expected


def test_simulated_state_estimator_flags() -> None:
    estimator = SimulatedStateEstimator()

    assert estimator.estimate(3).flags["obstacle_detected"] is False
    assert estimator.estimate(4).flags["obstacle_detected"] is True


def test_state_estimator_is_abstract() -> None:
    assert hasattr(StateEstimator, "estimate")
