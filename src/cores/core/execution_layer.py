from typing import List
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_plan import ExecutionPlan
from cores.interfaces.module import ModuleResult


class ExecutionLayer:
    """
    ExecutionLayer handles executing the modules specified in an ExecutionPlan.

    It remains completely unaware of the EventBus, returning the results of module
    execution back to the Runtime orchestrator.
    """

    def execute(
        self,
        plan: ExecutionPlan,
        state: RobotState,
        context: RuntimeContext,
    ) -> List[ModuleResult]:
        """
        Execute modules in the order defined by the ExecutionPlan and return their results.
        """
        results = []
        for module in plan.modules:
            result = module.execute(state, context)
            results.append(result)
        return results
