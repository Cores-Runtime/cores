from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_plan import ExecutionPlan


class ExecutionLayer:
    """
    ExecutionLayer handles executing the modules specified in an ExecutionPlan.
    """

    def execute(
        self,
        plan: ExecutionPlan,
        state: RobotState,
        context: RuntimeContext,
    ) -> None:
        """
        Execute modules in the order defined by the ExecutionPlan.
        """
        pass
