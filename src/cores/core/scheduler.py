from abc import ABC, abstractmethod
from typing import List
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.execution_plan import ExecutionPlan
from cores.interfaces.module import Module
from cores.events.event import Event


class SchedulingPolicy(ABC):
    """
    Abstract base class for all scheduling policies in CORES.
    """

    @abstractmethod
    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        """
        Produce an ExecutionPlan based on available modules, robot state, context, and events.
        """
        pass


class DefaultSchedulingPolicy(SchedulingPolicy):
    """
    Default scheduling policy that executes all registered modules in their registered order.
    """

    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        # In Phase 1, the default policy simply schedules all registered modules in order.
        return ExecutionPlan(modules=modules.copy())


class OperatorSchedulingPolicy(SchedulingPolicy):
    """
    Baseline Operator scheduling policy.

    Orders modules by priority (higher first). Modules with equal priority
    retain their registration order. No optimization algorithms.
    """

    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        sorted_modules = sorted(
            modules,
            key=lambda module: module.priority,
            reverse=True,
        )
        return ExecutionPlan(modules=sorted_modules)


class Scheduler:
    """
    Scheduler decides which cognitive modules execute next using a SchedulingPolicy.

    It operates as a pure coordinator, delegating the planning decision to its
    configured SchedulingPolicy. It does not maintain event queues or execution state.
    """

    def __init__(self, policy: SchedulingPolicy) -> None:
        self.policy = policy

    def schedule(
        self,
        modules: List[Module],
        state: RobotState,
        context: RuntimeContext,
        events: List[Event],
    ) -> ExecutionPlan:
        """
        Generate an execution schedule based on inputs and the active policy.
        """
        return self.policy.schedule(modules, state, context, events)
