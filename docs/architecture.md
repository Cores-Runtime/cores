# CORES Runtime - Architecture

## System Overview

CORES (Cognitive Operating Runtime for Embodied Systems) is a deterministic, modular, synchronous runtime designed to orchestrate cognitive modules on an embodied robot.

The architecture is optimized for:
- **Simplicity**: Every component has one clearly defined responsibility.
- **Determinism**: Given identical inputs, the runtime always produces identical outputs.
- **Modularity**: The filesystem structure mirrors the logical component structure.
- **Testability**: All components are independently testable with no hidden dependencies.

---

## Component Map

```
cores/
├── src/cores/
│   ├── core/
│   │   ├── robot_state.py        Single source of truth for system state
│   │   ├── runtime_context.py    Execution metadata (cycle count, mode, budgets)
│   │   ├── execution_plan.py     Immutable execution contract from Scheduler
│   │   ├── execution_layer.py    Executes modules from ExecutionPlan
│   │   ├── scheduler.py          SchedulingPolicy ABC + Scheduler coordinator
│   │   ├── memory/               Memory cognitive node (episodic + semantic + Logger)
│   │   │   ├── interface.py      MemoryRecord, MemoryQuery, MemoryStrategy, Memory
│   │   │   ├── store.py          EpisodicStore, SemanticStore
│   │   │   ├── types.py          MemoryType, RecordLifecycle, NarrativeRecord
│   │   │   └── strategies/       FIFO, Priority, TimeDecay, Episodic
│   │   ├── mission_manager/      Mission Manager (lifecycle + goal selection)
│   │   │   ├── types.py          MissionStatus, GoalStatus, MissionRecord, MissionContext
│   │   │   ├── policies.py       Selection / Failure / Retry / Transition policies
│   │   │   ├── constraints.py    Optional automatic goal completion
│   │   │   └── manager.py        MissionManager orchestrator
│   │   ├── logger/               Consolidation engine inside Memory
│   │   │   ├── interface.py      LoggerStrategy ABC
│   │   │   ├── logger.py         Logger orchestrator
│   │   │   ├── spsca.py          SPSCALogger (LoggerStrategy)
│   │   │   └── triggers.py       Capacity / Count / Idle / Composite triggers
│   │   └── runtime.py            Orchestrates the full execution cycle
│   ├── events/
│   │   ├── event.py              Frozen, immutable Event model
│   │   ├── event_bus.py          Stateless publish/subscribe transport
│   │   └── event_type.py         StrEnum of all valid event types
│   └── interfaces/
│       └── module.py             Module ABC, ModuleResult, ModuleStatus
```

---

## Execution Cycle

One call to `Runtime.step()` executes this exact sequence:

```
1. State Estimation   estimator.estimate() updates RobotState
        ↓
2. Mission Manager    picks the active mission and active goal
        ↓
3. Memory             store observations, consolidate, forget
        ↓
4. Planning           plan (or replan) for the single active goal
        ↓
5. Events             flush _buffered_events from previous cycle
        ↓
6. Schedule           scheduler.schedule(modules, state, context, events)
        ↓
7. Execute            execution_layer.execute(plan, state, context)
        ↓
8. Mission Manager    observes execution results (progress, completion)
        ↓
9. Publish            Runtime publishes runtime state through the bridge
        ↓
10. Advance Context   context.cycle_count += 1
```

---

## Dependency Rules

| Component | May depend on | Must NOT depend on |
|---|---|---|
| `Event` | nothing | everything |
| `EventType` | nothing | everything |
| `EventBus` | `Event`, `EventType` | `Runtime`, `Scheduler`, `Module` |
| `RobotState` | nothing | everything |
| `RuntimeContext` | nothing | everything |
| `ExecutionPlan` | `Module` interface | `Runtime`, `EventBus` |
| `Module` | `RobotState`, `RuntimeContext`, `Event` | `Runtime`, `Scheduler`, `EventBus` |
| `ExecutionLayer` | `ExecutionPlan`, `ModuleResult` | `EventBus`, `Scheduler`, `Runtime` |
| `SchedulingPolicy` | `RobotState`, `RuntimeContext`, `Event`, `ExecutionPlan` | `Runtime`, `EventBus` |
| `Scheduler` | `SchedulingPolicy` | `Runtime`, `EventBus` |
| `MissionManager` | `RobotState`, `RuntimeContext`, `Mission`, `Goal` | `Planner`, `Scheduler`, `EventBus`, `Memory` |
| `Runtime` | all of the above | nothing external |

---

## Event Flow

```
Module.execute()
    → returns ModuleResult(events=[...])
        → ExecutionLayer returns List[ModuleResult] to Runtime
            → Runtime publishes each event via event_bus.publish()
                → EventBus dispatches synchronously to subscribers
                    → Runtime._on_event() appends to _buffered_events
                        → Next cycle: events passed to Scheduler
```

---

## Design Invariants

1. `RobotState` is the single source of truth. StateEstimation and MissionManager write to it; all other components read it.
2. `Scheduler` is the only component that produces execution plans.
3. `ExecutionLayer` is the only component that invokes `module.execute()`.
4. `EventBus` has no knowledge of any other runtime component.
5. All execution in Phase 1 is synchronous and single-threaded.
