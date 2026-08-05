"""Safety Supervisor Demo (Phase 7).

Scenario:
1. Mission starts normally (battery 80%).
2. Battery drops to 25% (warning threshold) -> PAUSE.
3. Battery drops to 10% (critical threshold) -> EMERGENCY_STOP.

Each decision is printed clearly in the console.
"""

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.safety_supervisor import (
    SafetySupervisor,
    BatterySafetyPolicy,
)


def print_decision(label: str, state: RobotState, supervisor: SafetySupervisor) -> None:
    context = RuntimeContext()
    result = supervisor.evaluate(state, context)
    battery_str = f"{state.battery_level * 100:.0f}%" if state.battery_level is not None else "N/A"
    print(
        f"[{label}] Battery: {battery_str} | "
        f"Decision: {result.decision.value.upper()} | "
        f"Reason: {result.reason.value} | "
        f"Policy: {result.triggering_policy}"
    )


def main() -> None:
    print("=" * 70)
    print("Safety Supervisor Demo")
    print("=" * 70)
    print()

    supervisor = SafetySupervisor()

    # Step 1: Normal operation (battery 80%)
    print_decision("1. Mission starts normally", RobotState(battery_level=0.80), supervisor)

    # Step 2: Low battery (25%) -> should PAUSE
    print_decision("2. Battery drops to warning level", RobotState(battery_level=0.25), supervisor)

    # Step 3: Battery slightly below warning (24%) -> should PAUSE
    print_decision("3. Battery continues dropping", RobotState(battery_level=0.24), supervisor)

    # Step 4: Critical battery (10%) -> should EMERGENCY_STOP
    print_decision("4. Battery hits critical level", RobotState(battery_level=0.10), supervisor)

    # Step 5: Below critical (5%) -> should EMERGENCY_STOP
    print_decision("5. Battery below critical", RobotState(battery_level=0.05), supervisor)

    # Step 6: Demonstrate custom thresholds
    print()
    print("-" * 70)
    print("Custom Thresholds Demo")
    print("-" * 70)
    custom_supervisor = SafetySupervisor()
    # Replace default battery policy with stricter thresholds
    custom_supervisor.composite_policy.remove_policy("BatterySafetyPolicy")
    custom_supervisor.register_policy(
        BatterySafetyPolicy(critical_threshold=0.20, warning_threshold=0.40)
    )

    print_decision("6. Custom: battery 35% (below 40% warning)", RobotState(battery_level=0.35), custom_supervisor)
    print_decision("7. Custom: battery 15% (below 20% critical)", RobotState(battery_level=0.15), custom_supervisor)

    # Step 7: Demonstrate human detection (EMERGENCY_STOP)
    print()
    print("-" * 70)
    print("Human Detection Demo")
    print("-" * 70)
    print_decision(
        "8. Human detected",
        RobotState(battery_level=0.80, flags={"human_detected": True}),
        supervisor,
    )

    # Step 8: Demonstrate sensor failure
    print()
    print("-" * 70)
    print("Sensor Failure Demo")
    print("-" * 70)
    print_decision(
        "9. Lidar failed",
        RobotState(battery_level=0.80, sensor_summaries={"lidar": "failed"}),
        supervisor,
    )
    print_decision(
        "10. Camera degraded",
        RobotState(battery_level=0.80, sensor_summaries={"camera": "degraded"}),
        supervisor,
    )

    # Step 9: Demonstrate temperature issue
    print()
    print("-" * 70)
    print("Temperature Demo")
    print("-" * 70)
    print_decision(
        "11. Temperature high (75C)",
        RobotState(battery_level=0.80, sensor_summaries={"temperature": 75.0}),
        supervisor,
    )
    print_decision(
        "12. Temperature critical (90C)",
        RobotState(battery_level=0.80, sensor_summaries={"temperature": 90.0}),
        supervisor,
    )

    print()
    print("=" * 70)
    print("Demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
