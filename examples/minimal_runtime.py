"""
Minimal CORES runtime demonstration.

Runs three complete runtime cycles with simulated state, priority-based
scheduling, and readable log output.
"""

import logging
import sys

from cores.core import (
    ExecutionLayer,
    OperatorSchedulingPolicy,
    Runtime,
    Scheduler,
    SimulatedStateEstimator,
)
from cores.events import Event, EventType
from cores.interfaces import Module, ModuleResult, ModuleStatus
from cores.core import RobotState, RuntimeContext


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("cores.example")


class TelemetryModule(Module):
    """Low-priority module that emits diagnostic events."""

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        logger.info(
            "  [%s] battery=%.2f pose_x=%.1f mission=%s",
            self.name,
            state.battery_level,
            state.pose.get("x", 0.0),
            state.mission_status,
        )
        return ModuleResult(
            module_name=self.name,
            status=ModuleStatus.SUCCESS,
            events=[
                Event(
                    source=self.name,
                    event_type=EventType.DIAGNOSTIC,
                    payload={"cycle": context.cycle_count},
                )
            ],
        )


class SafetyModule(Module):
    """High-priority module that checks safety flags."""

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        obstacle = state.flags.get("obstacle_detected", False)
        logger.info("  [%s] obstacle_detected=%s", self.name, obstacle)
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


def main() -> None:
    logger.info("=== CORES Minimal Runtime Example ===")

    runtime = Runtime(
        scheduler=Scheduler(OperatorSchedulingPolicy()),
        execution_layer=ExecutionLayer(),
        state_estimator=SimulatedStateEstimator(),
    )

    runtime.register_module(TelemetryModule("telemetry", priority=1))
    runtime.register_module(SafetyModule("safety_monitor", priority=10))

    for cycle in range(3):
        logger.info("--- Cycle %d ---", cycle)
        runtime.step()
        logger.info(
            "  State: battery=%.2f x=%.1f status=%s",
            runtime.state.battery_level,
            runtime.state.pose.get("x", 0.0),
            runtime.state.mission_status,
        )
        logger.info("  Buffered events: %d", len(runtime._buffered_events))

    logger.info("=== Complete (%d cycles) ===", runtime.context.cycle_count)


if __name__ == "__main__":
    main()
