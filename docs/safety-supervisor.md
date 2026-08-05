# Safety Supervisor

## What It Does

The Safety Supervisor is the highest decision-making layer in the runtime. It answers one question:

> Is it safe for the robot to continue doing this?

It never plans, schedules, executes, or estimates state. It only evaluates the current state and returns a decision.

## Why It Exists

Before this phase, nothing in the runtime could decide whether the robot should continue at all. Planning decides how to achieve a goal. The Mission Manager decides which goal is active. But nothing asks whether the robot should stop because of low battery, a nearby obstacle, or a detected human.

The Safety Supervisor fills that gap. It sits between State Estimation and Mission Manager, evaluating every cycle before any decisions are made.

## Runtime Position

```
1. State Estimation
2. Safety Supervisor     <-- evaluates state, returns decision
3. Mission Manager
4. Memory
5. Planning
6. Scheduler
7. Execution
8. Memory Outcomes
9. Publish State
```

Safety always runs after State Estimation and before Mission Manager. If Safety returns EMERGENCY_STOP, the cycle ends immediately: no Mission Manager, no Memory, no Planning, no Execution.

## Safety Decisions

Each cycle, the Safety Supervisor returns exactly one decision:

```
EMERGENCY_STOP
      ^
CANCEL_MISSION
      ^
PAUSE
      ^
ALLOW
```

The decision represents the highest-priority safety concern across all registered policies.

- **ALLOW**: continue normally.
- **PAUSE**: Mission Manager pauses the current mission. The robot stops but retains state.
- **CANCEL_MISSION**: Mission Manager cancels the mission entirely.
- **EMERGENCY_STOP**: the cycle terminates. No further processing. The robot stops immediately.

## Safety Policies

Safety behavior is policy-based. Each policy evaluates the current state independently and returns a decision. Policies must not depend on each other's outputs.

### Built-in Policies

| Policy | Reads From | Returns PAUSE When | Returns CANCEL When | Returns EMERGENCY_STOP When |
|--------|-----------|-------------------|-------------------|---------------------------|
| BatterySafetyPolicy | `state.battery_level` | below warning threshold | - | below critical threshold |
| CollisionSafetyPolicy | `state.sensor_summaries["collision_distance"]` | below warning distance | - | below critical distance |
| HumanSafetyPolicy | `state.flags["human_detected"]` | - | - | human detected |
| TemperatureSafetyPolicy | `state.sensor_summaries["temperature"]` | above warning threshold | - | above critical threshold |
| SensorFailurePolicy | `state.sensor_summaries` | sensor degraded | critical sensor failed | - |

All policies return ALLOW when their required data is missing from state. This makes them optional capabilities that activate only when relevant information is available.

### Policy Configuration

Policies receive configuration through constructors. No hardcoded thresholds.

```python
BatterySafetyPolicy(
    critical_threshold=0.10,
    warning_threshold=0.25
)
```

Custom thresholds:

```python
BatterySafetyPolicy(
    critical_threshold=0.20,
    warning_threshold=0.40
)
```

## Composite Safety Policy

The CompositeSafetyPolicy owns multiple policies and returns the highest-priority decision.

- Evaluates all policies each cycle.
- Short-circuits on EMERGENCY_STOP (terminal decision).
- Tie-breaks by registration order (first registered wins).
- Deterministic: same inputs always produce the same decision.

## SafetySupervisor

The SafetySupervisor is the public interface. It owns a CompositeSafetyPolicy and provides convenience methods.

```python
from cores.core.safety_supervisor import SafetySupervisor

supervisor = SafetySupervisor()
# Comes with 5 default policies

result = supervisor.evaluate(state, context)
print(result.decision)      # SafetyDecision
print(result.reason)        # SafetyReason
print(result.triggering_policy)  # str
```

### Custom Policies

```python
from cores.core.safety_supervisor import SafetySupervisor, CompositeSafetyPolicy

composite = CompositeSafetyPolicy()
composite.add_policy(MyCustomPolicy())
supervisor = SafetySupervisor(composite_policy=composite)
```

## Runtime Integration

The Runtime stores the safety result in `context.metrics["safety_result"]`. This makes it available for traces, benchmarks, and debugging without adding state to RuntimeContext.

```python
runtime.step()
result = runtime.context.metrics["safety_result"]
```

On EMERGENCY_STOP, the Runtime:
1. Stores the safety result.
2. Skips Mission Manager.
3. Skips Memory.
4. Skips Planning.
5. Skips Scheduler.
6. Skips Execution.
7. Publishes state.
8. Ends the cycle.

No additional runtime state is set. The safety result in metrics tells everyone what happened.

## Testing

37 tests covering:
- Battery threshold behavior (critical, warning, normal, None)
- Collision policy (critical, warning, normal, missing sensor)
- Human detection (detected, not detected)
- Temperature policy (critical, warning, normal, missing)
- Sensor failure (critical failed, degraded, all ok, missing)
- Composite priority ordering and short-circuit
- Tie-break by registration order
- SafetySupervisor API (evaluate, current_decision, register_policy, remove_policy)
- Real Runtime integration (execution order, EMERGENCY_STOP skips, PAUSE/CANCEL calls mission manager)
