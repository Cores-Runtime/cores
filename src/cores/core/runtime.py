from typing import List, Optional
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_layer import ExecutionLayer
from cores.core.scheduler import Scheduler
from cores.core.state_estimator import StateEstimator
from cores.core.module_registry import ModuleRegistry
from cores.core.world_model import WorldModelStrategy, SimpleObjectRegistry
from cores.core.state_estimation import StateEstimation
from cores.core.memory import Memory, MemoryRecord, MemoryType

from cores.core.planning.interface import Planner, PlanningContext
from cores.core.planning.mission import Mission
from cores.core.mission_manager import MissionManager, MissionContext
from cores.core.safety_supervisor import SafetySupervisor, SafetyDecision
from cores.events.event_bus import EventBus
from cores.events.event import Event
from cores.events.event_type import EventType
from cores.interfaces.module import Module, ModuleResult
from cores.runtime.runtime_bridge import RuntimeBridge, InMemoryRuntimeBridge, RuntimeStateBuilder


class Runtime:
    """
    Runtime is the central orchestrator of the CORES execution cycle.

    It owns all core runtime components (State, Context, EventBus, Scheduler, ExecutionLayer)
    and manages the step-by-step pipeline of a single execution cycle.
    """

    def __init__(
        self,
        scheduler: Scheduler,
        execution_layer: ExecutionLayer,
        state_estimator: Optional[StateEstimator] = None,
        bridge: Optional[RuntimeBridge] = None,
        world_model: Optional[WorldModelStrategy] = None,
        planner: Optional[Planner] = None,
        mission: Optional[Mission] = None,
        mission_manager: Optional[MissionManager] = None,
        memory: Optional[Memory] = None,
        safety_supervisor: Optional[SafetySupervisor] = None,
    ) -> None:
        self.state_estimator = state_estimator
        self.state = RobotState()
        self.context = RuntimeContext()
        self.event_bus = EventBus()
        self.scheduler = scheduler
        self.execution_layer = execution_layer
        self.bridge = bridge or InMemoryRuntimeBridge()
        self._state_builder = RuntimeStateBuilder()

        self.module_registry = ModuleRegistry()
        strategy = world_model or SimpleObjectRegistry()
        self.state_estimation = StateEstimation(strategy=strategy)
        self.world_model = strategy
        self._buffered_events: List[Event] = []
        self._last_module_results: List[ModuleResult] = []
        self._last_decision_time_ms: float = 0.0

        self.planner = planner
        self.mission = mission or Mission(mission_id="default", goals=[])
        self._last_planning_result = None

        self.mission_manager = mission_manager
        if self.mission_manager is None:
            self.mission_manager = MissionManager(
                missions=[mission] if mission is not None else []
            )

        self.memory = memory or Memory()

        self.safety_supervisor = safety_supervisor or SafetySupervisor()

        for event_type in EventType:
            self.event_bus.subscribe(event_type, self._on_event)

    @property
    def modules(self) -> List[Module]:
        return self.module_registry.get_all()

    def register_module(self, module: Module) -> None:
        """
        Register a module to be managed by the runtime.
        """
        try:
            self.module_registry.register(module, runtime=self)
            module.on_startup()
        except ValueError:
            pass

    def _on_event(self, event: Event) -> None:
        """
        Internal handler to buffer incoming events for the next scheduling cycle.
        """
        self._buffered_events.append(event)

    def step(self) -> None:
        """
        Execute one complete, sequential runtime cycle:
        1. Wire shared strategy into context for observation modules.
        2. Estimate robot state.
        3. Safety Supervisor evaluates state and returns decision.
        4. Select the active mission and goal (Mission Manager).
        5. Memory cognitive loop (store, consolidate, forget).
        6. Run the Planner (propose candidate plans, informed by memory).
        7. Schedule and execute all registered modules.
        8. Store outcomes into Episodic Memory.
        9. Publish runtime state snapshot through the bridge.
        """
        # 1. Wire shared components into context
        self.context.world_model = self.state_estimation.strategy
        self.context.memory = self.memory

        # 2. State estimation
        if self.state_estimator is not None:
            self.state = self.state_estimator.estimate(self.context.cycle_count)

        # 3. Safety Supervisor evaluates state
        safety_result = self.safety_supervisor.evaluate(self.state, self.context)
        self.context.metrics["safety_result"] = safety_result

        # 4. If EMERGENCY_STOP, skip everything and publish state
        if safety_result.decision == SafetyDecision.EMERGENCY_STOP:
            self._publish_runtime_state([])
            return

        # 5. Mission selection - which mission and goal are active right now
        mission_context = self.mission_manager.execute(self.state, self.context)

        # 6. Handle PAUSE and CANCEL_MISSION from Safety
        current_mission = self.mission_manager.current_mission()
        if current_mission is not None:
            if safety_result.decision == SafetyDecision.PAUSE:
                self.mission_manager.pause(current_mission.mission_id)
            elif safety_result.decision == SafetyDecision.CANCEL_MISSION:
                self.mission_manager.cancel(current_mission.mission_id)

        # 7. Memory — store observations, consolidate, forget
        memory_result = self.memory.execute(self.state, self.context)
        self._last_module_results.append(memory_result)

        # 8. Planning — run the cognitive planner if configured
        if self.planner is not None:
            pctx = PlanningContext(
                cycle_count=self.context.cycle_count,
                compute_budget=self.context.compute_budget,
                time_budget_ms=self.context.time_budget_ms,
                world_state={"obstacle_count": self.state_estimation.strategy.obstacle_count},
                environment_changed=self.state_estimation.last_environment_changed,
                change_set=self.state_estimation.last_change_set,
                memory=self.memory,
            )
            planning_mission = self._planning_mission(mission_context)
            previous = None
            if self._last_planning_result is not None:
                previous = self._last_planning_result.selected
            if pctx.environment_changed and previous is not None:
                result = self.planner.replan(
                    self.state, planning_mission, pctx, previous, changes=pctx.change_set
                )
                if result is None:
                    result = self.planner.plan(self.state, planning_mission, pctx)
            else:
                result = self.planner.plan(self.state, planning_mission, pctx)
            self._last_planning_result = result
            self.context.metrics["planning_result"] = result
        else:
            self._last_planning_result = None

        # 9. Collect and flush buffered events
        events_to_process = self._buffered_events.copy()
        self._buffered_events.clear()

        # 10. Schedule and execute all registered modules
        plan = self.scheduler.schedule(
            self.modules, self.state, self.context, events_to_process
        )
        results = self.execution_layer.execute(plan, self.state, self.context)
        self._last_module_results = list(results)
        for result in results:
            for event in result.events:
                self.event_bus.publish(event)

        # 11. Mission Manager observes what execution produced
        self.mission_manager.observe_execution(results, self.state)

        # 12. Store outcomes into Episodic Memory
        for result in results:
            outcome_record = MemoryRecord(
                id=f"outcome_{result.module_name}_{self.context.cycle_count}",
                content={
                    "action": result.module_name,
                    "result": result.status.value,
                    "cycle": self.context.cycle_count,
                },
                cycle=self.context.cycle_count,
                importance=0.8,
                record_type=MemoryType.OUTCOME,
            )
            self.memory.store(outcome_record)

        # 13. StateEstimation cognitive loop — runs after all observation modules
        state_estimation_result = self.state_estimation.execute(self.state, self.context)
        self._last_module_results.append(state_estimation_result)

        # 14. Capture decision time from context metrics
        self._last_decision_time_ms = float(
            self.context.metrics.get("decision_time_ms", 0.0)
        )

        # 15. Post-execution cycle maintenance
        self.context.cycle_count += 1

        # 16. Build runtime state snapshot and publish through bridge
        self._publish_runtime_state(events_to_process)

    def _publish_runtime_state(self, events_to_process: List[Event]) -> None:
        """Build and publish runtime state snapshot through the bridge."""
        runtime_state = self._state_builder.build(
            state=self.state,
            context=self.context,
            modules=self.modules,
            module_results=self._last_module_results,
            cycle_events=list(events_to_process),
            decision_time_ms=self._last_decision_time_ms,
            state_estimation=self.state_estimation,
            planning_result=self._last_planning_result,
        )
        self.bridge.publish(runtime_state)

    def shutdown(self) -> None:
        for module in self.module_registry.get_all():
            try:
                module.on_shutdown()
            except Exception:
                pass
        self.bridge.close()

    def _planning_mission(self, context: MissionContext) -> Mission:
        """Planning sees one active goal only, never the mission queue."""
        if (
            context.is_active
            and context.current_mission is not None
            and context.current_goal is not None
        ):
            return Mission(
                mission_id=context.current_mission.mission_id,
                goals=[context.current_goal],
                metadata=dict(context.mission_metadata),
            )
        return Mission(mission_id="default", goals=[])

