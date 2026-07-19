from typing import List, Optional
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_layer import ExecutionLayer
from cores.core.scheduler import Scheduler
from cores.core.state_estimator import StateEstimator
from cores.core.module_registry import ModuleRegistry
from cores.core.world_model import WorldModelStrategy, SimpleObjectRegistry
from cores.core.state_estimation import StateEstimation
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
        3. Collect events from the previous cycle.
        4. Schedule and execute all registered modules.
        5. Run the StateEstimation's cognitive loop (predict, check, explain).
        6. Publish runtime state snapshot through the bridge.
        7. Advance runtime context metadata.
        """
        # 1. Wire the StateEstimation's reasoning strategy into context
        self.context.world_model = self.state_estimation.strategy

        # 2. State estimation
        if self.state_estimator is not None:
            self.state = self.state_estimator.estimate(self.context.cycle_count)

        # 3. Collect and flush buffered events
        events_to_process = self._buffered_events.copy()
        self._buffered_events.clear()

        # 4. Planning and execution of all modules (observation, planning, etc.)
        plan = self.scheduler.schedule(
            self.modules, self.state, self.context, events_to_process
        )
        results = self.execution_layer.execute(plan, self.state, self.context)
        self._last_module_results = list(results)
        for result in results:
            for event in result.events:
                self.event_bus.publish(event)

        # 5. StateEstimation cognitive loop — runs after all observation modules
        state_estimation_result = self.state_estimation.execute(self.state, self.context)
        self._last_module_results.append(state_estimation_result)

        # 6. Capture decision time from context metrics
        self._last_decision_time_ms = float(
            self.context.metrics.get("decision_time_ms", 0.0)
        )

        # 7. Post-execution cycle maintenance
        self.context.cycle_count += 1

        # 8. Build runtime state snapshot and publish through bridge
        runtime_state = self._state_builder.build(
            state=self.state,
            context=self.context,
            modules=self.modules,
            module_results=self._last_module_results,
            cycle_events=list(events_to_process),
            decision_time_ms=self._last_decision_time_ms,
            state_estimation=self.state_estimation,
        )
        self.bridge.publish(runtime_state)

    def shutdown(self) -> None:
        for module in self.module_registry.get_all():
            try:
                module.on_shutdown()
            except Exception:
                pass
        self.bridge.close()

