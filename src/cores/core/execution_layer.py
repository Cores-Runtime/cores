from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_plan import ExecutionPlan
from cores.events.event_bus import EventBus


class ExecutionLayer:
    """
    ExecutionLayer handles executing the modules specified in an ExecutionPlan.
    """

    def execute(
        self,
        plan: ExecutionPlan,
        state: RobotState,
        context: RuntimeContext,
        event_bus: EventBus,
    ) -> None:
        """
        Execute modules in the order defined by the ExecutionPlan and publish their events.
        """
        for module in plan.modules:
            result = module.execute(state, context)
            for event in result.events:
                event_bus.publish(event)
