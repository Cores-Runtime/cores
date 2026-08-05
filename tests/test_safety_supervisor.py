"""Tests for the Safety Supervisor (Phase 7)."""

from unittest.mock import MagicMock

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.safety_supervisor.types import (
    SafetyDecision,
    SafetyReason,
    SafetyResult,
    SafetyPolicyResult,
)
from cores.core.safety_supervisor.policies import (
    BatterySafetyPolicy,
    CollisionSafetyPolicy,
    HumanSafetyPolicy,
    TemperatureSafetyPolicy,
    SensorFailurePolicy,
    CompositeSafetyPolicy,
)
from cores.core.safety_supervisor.manager import SafetySupervisor
from cores.core import (
    Runtime,
    Scheduler,
    DefaultSchedulingPolicy,
    ExecutionLayer,
    ExecutionPlan,
    SimulatedStateEstimator,
    MissionManager,
)
from cores.core.planning.mission import Mission
from cores.core.planning.types import Goal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(**kwargs) -> RobotState:
    defaults = {"battery_level": 1.0}
    defaults.update(kwargs)
    return RobotState(**defaults)


def _context(**kwargs) -> RuntimeContext:
    return RuntimeContext(**kwargs)


# ---------------------------------------------------------------------------
# Battery Safety Policy
# ---------------------------------------------------------------------------


class TestBatterySafetyPolicy:
    def test_normal_battery_allows(self) -> None:
        policy = BatterySafetyPolicy()
        result = policy.evaluate(_state(battery_level=0.5), _context())
        assert result.decision == SafetyDecision.ALLOW

    def test_low_battery_pauses(self) -> None:
        policy = BatterySafetyPolicy()
        result = policy.evaluate(_state(battery_level=0.20), _context())
        assert result.decision == SafetyDecision.PAUSE
        assert result.reason == SafetyReason.BATTERY_LOW

    def test_critical_battery_emergency_stops(self) -> None:
        policy = BatterySafetyPolicy()
        result = policy.evaluate(_state(battery_level=0.05), _context())
        assert result.decision == SafetyDecision.EMERGENCY_STOP
        assert result.reason == SafetyReason.BATTERY_CRITICAL

    def test_none_battery_allows(self) -> None:
        policy = BatterySafetyPolicy()
        result = policy.evaluate(_state(battery_level=None), _context())
        assert result.decision == SafetyDecision.ALLOW

    def test_custom_thresholds(self) -> None:
        policy = BatterySafetyPolicy(critical_threshold=0.20, warning_threshold=0.40)
        result = policy.evaluate(_state(battery_level=0.30), _context())
        assert result.decision == SafetyDecision.PAUSE


# ---------------------------------------------------------------------------
# Collision Safety Policy
# ---------------------------------------------------------------------------


class TestCollisionSafetyPolicy:
    def test_normal_distance_allows(self) -> None:
        policy = CollisionSafetyPolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"collision_distance": 1.0}), _context()
        )
        assert result.decision == SafetyDecision.ALLOW

    def test_warning_distance_pauses(self) -> None:
        policy = CollisionSafetyPolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"collision_distance": 0.5}), _context()
        )
        assert result.decision == SafetyDecision.PAUSE
        assert result.reason == SafetyReason.COLLISION_RISK

    def test_critical_distance_emergency_stops(self) -> None:
        policy = CollisionSafetyPolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"collision_distance": 0.1}), _context()
        )
        assert result.decision == SafetyDecision.EMERGENCY_STOP
        assert result.reason == SafetyReason.COLLISION_RISK

    def test_missing_sensor_allows(self) -> None:
        policy = CollisionSafetyPolicy()
        result = policy.evaluate(_state(), _context())
        assert result.decision == SafetyDecision.ALLOW


# ---------------------------------------------------------------------------
# Human Safety Policy
# ---------------------------------------------------------------------------


class TestHumanSafetyPolicy:
    def test_no_human_allows(self) -> None:
        policy = HumanSafetyPolicy()
        result = policy.evaluate(_state(), _context())
        assert result.decision == SafetyDecision.ALLOW

    def test_human_detected_emergency_stops(self) -> None:
        policy = HumanSafetyPolicy()
        result = policy.evaluate(
            _state(flags={"human_detected": True}), _context()
        )
        assert result.decision == SafetyDecision.EMERGENCY_STOP
        assert result.reason == SafetyReason.HUMAN_DETECTED


# ---------------------------------------------------------------------------
# Temperature Safety Policy
# ---------------------------------------------------------------------------


class TestTemperatureSafetyPolicy:
    def test_normal_temperature_allows(self) -> None:
        policy = TemperatureSafetyPolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"temperature": 50.0}), _context()
        )
        assert result.decision == SafetyDecision.ALLOW

    def test_high_temperature_pauses(self) -> None:
        policy = TemperatureSafetyPolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"temperature": 75.0}), _context()
        )
        assert result.decision == SafetyDecision.PAUSE
        assert result.reason == SafetyReason.TEMPERATURE_HIGH

    def test_critical_temperature_emergency_stops(self) -> None:
        policy = TemperatureSafetyPolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"temperature": 90.0}), _context()
        )
        assert result.decision == SafetyDecision.EMERGENCY_STOP
        assert result.reason == SafetyReason.TEMPERATURE_CRITICAL

    def test_missing_sensor_allows(self) -> None:
        policy = TemperatureSafetyPolicy()
        result = policy.evaluate(_state(), _context())
        assert result.decision == SafetyDecision.ALLOW


# ---------------------------------------------------------------------------
# Sensor Failure Policy
# ---------------------------------------------------------------------------


class TestSensorFailurePolicy:
    def test_all_sensors_ok_allows(self) -> None:
        policy = SensorFailurePolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"lidar": "ok", "camera": "ok", "gps": "ok"}),
            _context(),
        )
        assert result.decision == SafetyDecision.ALLOW

    def test_critical_sensor_failed_cancels(self) -> None:
        policy = SensorFailurePolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"lidar": "failed"}), _context()
        )
        assert result.decision == SafetyDecision.CANCEL_MISSION
        assert result.reason == SafetyReason.SENSOR_FAILED

    def test_degraded_sensor_pauses(self) -> None:
        policy = SensorFailurePolicy()
        result = policy.evaluate(
            _state(sensor_summaries={"camera": "degraded"}), _context()
        )
        assert result.decision == SafetyDecision.PAUSE
        assert result.reason == SafetyReason.SENSOR_DEGRADED

    def test_missing_sensors_allows(self) -> None:
        policy = SensorFailurePolicy()
        result = policy.evaluate(_state(), _context())
        assert result.decision == SafetyDecision.ALLOW


# ---------------------------------------------------------------------------
# Composite Safety Policy
# ---------------------------------------------------------------------------


class TestCompositeSafetyPolicy:
    def test_empty_composite_allows(self) -> None:
        composite = CompositeSafetyPolicy()
        result = composite.evaluate(_state(), _context())
        assert result.decision == SafetyDecision.ALLOW

    def test_highest_priority_wins(self) -> None:
        composite = CompositeSafetyPolicy()
        composite.add_policy(BatterySafetyPolicy(warning_threshold=0.5))
        composite.add_policy(HumanSafetyPolicy())
        result = composite.evaluate(
            _state(battery_level=0.3, flags={"human_detected": True}), _context()
        )
        assert result.decision == SafetyDecision.EMERGENCY_STOP
        assert result.reason == SafetyReason.HUMAN_DETECTED

    def test_emergency_stop_short_circuits(self) -> None:
        composite = CompositeSafetyPolicy()
        # Add a policy that would return EMERGENCY_STOP
        composite.add_policy(HumanSafetyPolicy())
        # Add a policy that would return PAUSE (should not be evaluated)
        pause_policy = MagicMock()
        pause_policy.evaluate.return_value = MagicMock(
            decision=SafetyDecision.PAUSE, reason=SafetyReason.BATTERY_LOW, policy_name="pause"
        )
        composite.add_policy(pause_policy)
        result = composite.evaluate(
            _state(flags={"human_detected": True}), _context()
        )
        assert result.decision == SafetyDecision.EMERGENCY_STOP
        # pause_policy should not have been called due to short-circuit
        pause_policy.evaluate.assert_not_called()

    def test_tie_break_by_registration_order(self) -> None:
        composite = CompositeSafetyPolicy()
        policy_a = MagicMock()
        policy_a.evaluate.return_value = SafetyPolicyResult(
            decision=SafetyDecision.PAUSE, reason=SafetyReason.BATTERY_LOW, policy_name="A"
        )
        policy_b = MagicMock()
        policy_b.evaluate.return_value = SafetyPolicyResult(
            decision=SafetyDecision.PAUSE, reason=SafetyReason.TEMPERATURE_HIGH, policy_name="B"
        )
        composite.add_policy(policy_a)
        composite.add_policy(policy_b)
        result = composite.evaluate(_state(), _context())
        # Both return PAUSE, first registered wins
        assert result.policy_name == "A"

    def test_remove_policy(self) -> None:
        composite = CompositeSafetyPolicy()
        composite.add_policy(HumanSafetyPolicy())
        composite.remove_policy("HumanSafetyPolicy")
        result = composite.evaluate(
            _state(flags={"human_detected": True}), _context()
        )
        assert result.decision == SafetyDecision.ALLOW


# ---------------------------------------------------------------------------
# SafetySupervisor API
# ---------------------------------------------------------------------------


class TestSafetySupervisorAPI:
    def test_evaluate_returns_safety_result(self) -> None:
        supervisor = SafetySupervisor()
        result = supervisor.evaluate(_state(), _context())
        assert isinstance(result, SafetyResult)
        assert result.decision == SafetyDecision.ALLOW

    def test_current_decision_returns_last_decision(self) -> None:
        supervisor = SafetySupervisor()
        assert supervisor.current_decision() is None
        supervisor.evaluate(_state(), _context())
        assert supervisor.current_decision() == SafetyDecision.ALLOW

    def test_current_reason_returns_last_reason(self) -> None:
        supervisor = SafetySupervisor()
        assert supervisor.current_reason() is None
        supervisor.evaluate(_state(battery_level=0.05), _context())
        assert supervisor.current_reason() == SafetyReason.BATTERY_CRITICAL

    def test_register_policy(self) -> None:
        supervisor = SafetySupervisor()
        supervisor.register_policy(HumanSafetyPolicy())
        result = supervisor.evaluate(
            _state(flags={"human_detected": True}), _context()
        )
        assert result.decision == SafetyDecision.EMERGENCY_STOP

    def test_remove_policy(self) -> None:
        supervisor = SafetySupervisor()
        supervisor.register_policy(HumanSafetyPolicy())
        supervisor.remove_policy("HumanSafetyPolicy")
        result = supervisor.evaluate(
            _state(flags={"human_detected": True}), _context()
        )
        assert result.decision == SafetyDecision.ALLOW

    def test_composite_policy_property(self) -> None:
        supervisor = SafetySupervisor()
        assert isinstance(supervisor.composite_policy, CompositeSafetyPolicy)

    def test_custom_composite_policy(self) -> None:
        composite = CompositeSafetyPolicy()
        composite.add_policy(HumanSafetyPolicy())
        supervisor = SafetySupervisor(composite_policy=composite)
        result = supervisor.evaluate(
            _state(flags={"human_detected": True}), _context()
        )
        assert result.decision == SafetyDecision.EMERGENCY_STOP


# ---------------------------------------------------------------------------
# Runtime Integration (real Runtime, not mocked)
# ---------------------------------------------------------------------------


class TestRuntimeSafetyIntegration:
    """Integration tests verifying Safety Supervisor runs in the correct
    execution order within the Runtime cycle."""

    def _make_runtime(self, safety_supervisor: SafetySupervisor) -> Runtime:
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        state_estimator = SimulatedStateEstimator()
        runtime = Runtime(
            scheduler=scheduler,
            execution_layer=execution_layer,
            state_estimator=state_estimator,
            safety_supervisor=safety_supervisor,
        )
        return runtime

    def _make_runtime_with_mission_manager(
        self, safety_supervisor: SafetySupervisor, mission_manager: MissionManager
    ) -> Runtime:
        scheduler = Scheduler(DefaultSchedulingPolicy())
        execution_layer = ExecutionLayer()
        state_estimator = SimulatedStateEstimator()
        runtime = Runtime(
            scheduler=scheduler,
            execution_layer=execution_layer,
            state_estimator=state_estimator,
            safety_supervisor=safety_supervisor,
            mission_manager=mission_manager,
        )
        return runtime

    def test_safety_runs_after_state_estimation_before_mission_manager(self) -> None:
        """Verify the execution order: State Estimation -> Safety -> Mission Manager."""
        supervisor = SafetySupervisor()
        runtime = self._make_runtime(supervisor)

        # Track call order
        call_order = []
        original_estimate = runtime.state_estimator.estimate

        def tracking_estimate(cycle_count):
            call_order.append("state_estimation")
            return original_estimate(cycle_count)

        original_mission_execute = runtime.mission_manager.execute

        def tracking_mission_execute(state, context):
            call_order.append("mission_manager")
            return original_mission_execute(state, context)

        original_safety_evaluate = supervisor.evaluate

        def tracking_safety_evaluate(state, context):
            call_order.append("safety_supervisor")
            return original_safety_evaluate(state, context)

        runtime.state_estimator.estimate = tracking_estimate
        runtime.mission_manager.execute = tracking_mission_execute
        supervisor.evaluate = tracking_safety_evaluate

        # Mock scheduler/execution to avoid side effects
        runtime.scheduler.schedule = MagicMock(return_value=ExecutionPlan())
        runtime.execution_layer.execute = MagicMock(return_value=[])

        runtime.step()

        # Verify order
        assert call_order == ["state_estimation", "safety_supervisor", "mission_manager"]

    def test_emergency_stop_skips_execution(self) -> None:
        """Verify EMERGENCY_STOP skips Mission Manager, Memory, Planning, Scheduler, Execution."""
        supervisor = SafetySupervisor()
        supervisor.register_policy(HumanSafetyPolicy())
        runtime = self._make_runtime(supervisor)

        # Mock state_estimator to return state with human detected
        human_state = RobotState(flags={"human_detected": True})
        runtime.state_estimator.estimate = MagicMock(return_value=human_state)

        # Track which components are called
        called = []
        original_mission_execute = runtime.mission_manager.execute

        def tracking_mission_execute(state, context):
            called.append("mission_manager")
            return original_mission_execute(state, context)

        original_memory_execute = runtime.memory.execute

        def tracking_memory_execute(state, context):
            called.append("memory")
            return original_memory_execute(state, context)

        runtime.mission_manager.execute = tracking_mission_execute
        runtime.memory.execute = tracking_memory_execute
        runtime.scheduler.schedule = MagicMock(return_value=ExecutionPlan())
        runtime.execution_layer.execute = MagicMock(return_value=[])

        runtime.step()

        # Mission Manager, Memory, Scheduler, Execution should NOT be called
        assert "mission_manager" not in called
        assert "memory" not in called
        runtime.scheduler.schedule.assert_not_called()
        runtime.execution_layer.execute.assert_not_called()

    def test_pause_triggers_mission_manager_pause(self) -> None:
        """Verify PAUSE calls mission_manager.pause()."""
        supervisor = SafetySupervisor()
        supervisor.register_policy(BatterySafetyPolicy(warning_threshold=0.5))

        mission = Mission(mission_id="m1", goals=[Goal(goal_id="g1", description="g1")])
        mission_manager = MissionManager(missions=[mission])
        runtime = self._make_runtime_with_mission_manager(supervisor, mission_manager)

        # Mock state_estimator to return state with low battery
        low_battery_state = RobotState(battery_level=0.3)
        runtime.state_estimator.estimate = MagicMock(return_value=low_battery_state)

        # Mock pause to track calls
        runtime.mission_manager.pause = MagicMock()

        # Mock scheduler/execution
        runtime.scheduler.schedule = MagicMock(return_value=ExecutionPlan())
        runtime.execution_layer.execute = MagicMock(return_value=[])

        runtime.step()

        runtime.mission_manager.pause.assert_called_once_with("m1")

    def test_cancel_triggers_mission_manager_cancel(self) -> None:
        """Verify CANCEL_MISSION calls mission_manager.cancel()."""
        supervisor = SafetySupervisor()
        supervisor.register_policy(SensorFailurePolicy())

        mission = Mission(mission_id="m1", goals=[Goal(goal_id="g1", description="g1")])
        mission_manager = MissionManager(missions=[mission])
        runtime = self._make_runtime_with_mission_manager(supervisor, mission_manager)

        # Mock state_estimator to return state with sensor failure
        failed_sensor_state = RobotState(sensor_summaries={"lidar": "failed"})
        runtime.state_estimator.estimate = MagicMock(return_value=failed_sensor_state)

        # Mock cancel to track calls
        runtime.mission_manager.cancel = MagicMock()

        # Mock scheduler/execution
        runtime.scheduler.schedule = MagicMock(return_value=ExecutionPlan())
        runtime.execution_layer.execute = MagicMock(return_value=[])

        runtime.step()

        runtime.mission_manager.cancel.assert_called_once_with("m1")

    def test_safety_result_stored_in_context_metrics(self) -> None:
        """Verify safety_result is stored in context.metrics."""
        supervisor = SafetySupervisor()
        runtime = self._make_runtime(supervisor)

        # Mock scheduler/execution
        runtime.scheduler.schedule = MagicMock(return_value=ExecutionPlan())
        runtime.execution_layer.execute = MagicMock(return_value=[])

        runtime.step()

        assert "safety_result" in runtime.context.metrics
        assert isinstance(runtime.context.metrics["safety_result"], SafetyResult)

    def test_allow_continues_normally(self) -> None:
        """Verify ALLOW continues with normal execution."""
        supervisor = SafetySupervisor()
        runtime = self._make_runtime(supervisor)

        # Mock scheduler/execution
        runtime.scheduler.schedule = MagicMock(return_value=ExecutionPlan())
        runtime.execution_layer.execute = MagicMock(return_value=[])

        runtime.step()

        # Normal execution should happen
        runtime.scheduler.schedule.assert_called_once()
        runtime.execution_layer.execute.assert_called_once()
