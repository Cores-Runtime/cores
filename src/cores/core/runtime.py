from typing import List
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_layer import ExecutionLayer
from cores.core.scheduler import Scheduler
from cores.events.event_bus import EventBus
from cores.events.event import Event
from cores.events.event_type import EventType
from cores.interfaces.module import Module


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
    ) -> None:
        self.state = RobotState()
        self.context = RuntimeContext()
        self.event_bus = EventBus()
        self.scheduler = scheduler
        self.execution_layer = execution_layer

        self.modules: List[Module] = []
        self._buffered_events: List[Event] = []

        # Subscribe to all event types to collect them for the scheduler
        for event_type in EventType:
            self.event_bus.subscribe(event_type, self._on_event)

    def register_module(self, module: Module) -> None:
        """
        Register a module to be managed by the runtime.
        """
        if module not in self.modules:
            self.modules.append(module)

    def _on_event(self, event: Event) -> None:
        """
        Internal handler to buffer incoming events for the next scheduling cycle.
        """
        self._buffered_events.append(event)

    def step(self) -> None:
        """
        Execute one complete, sequential runtime cycle:
        1. Collect events from the previous cycle.
        2. Delegate planning to the Scheduler.
        3. Delegate plan execution to the ExecutionLayer.
        4. Advance runtime context metadata.
        """
        # 1. Collect and flush buffered events
        events_to_process = self._buffered_events.copy()
        self._buffered_events.clear()

        # 2. Planning Phase
        plan = self.scheduler.schedule(
            self.modules, self.state, self.context, events_to_process
        )

        # 3. Execution Phase
        self.execution_layer.execute(plan, self.state, self.context)

        # 4. Post-execution cycle maintenance
        self.context.cycle_count += 1
