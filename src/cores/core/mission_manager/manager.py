from __future__ import annotations

from typing import Dict, List, Optional

from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.planning.mission import Mission
from cores.core.planning.types import Goal
from cores.interfaces.module import ModuleResult

from cores.core.mission_manager.constraints import GoalConstraintEvaluator, NoAutoCompletion
from cores.core.mission_manager.policies import (
    DefaultMissionFailurePolicy,
    DefaultMissionTransitionPolicy,
    MissionFailurePolicy,
    MissionSelectionPolicy,
    MissionTransitionPolicy,
    PriorityMissionSelectionPolicy,
)
from cores.core.mission_manager.types import (
    FailureAction,
    GoalStatus,
    MissionContext,
    MissionRecord,
    MissionStatus,
)


class MissionManager:
    """Owns the mission and goal lifecycles.

    It decides which mission and which goal are active right now, and exposes
    them to Planning through a MissionContext that carries one active goal. It
    does not generate plans, execute actions, schedule modules, estimate
    state, or store memories.
    """

    def __init__(
        self,
        selection_policy: Optional[MissionSelectionPolicy] = None,
        failure_policy: Optional[MissionFailurePolicy] = None,
        transition_policy: Optional[MissionTransitionPolicy] = None,
        constraint_evaluator: Optional[GoalConstraintEvaluator] = None,
        missions: Optional[List[Mission]] = None,
    ) -> None:
        self.selection_policy = selection_policy or PriorityMissionSelectionPolicy()
        self.failure_policy = failure_policy or DefaultMissionFailurePolicy()
        self.transition_policy = transition_policy or DefaultMissionTransitionPolicy()
        self.constraint_evaluator = constraint_evaluator or NoAutoCompletion()
        self._records: Dict[str, MissionRecord] = {}
        self._active_mission_id: Optional[str] = None
        self._last_cleared: Optional[MissionRecord] = None
        if missions:
            for mission in missions:
                self.submit(mission)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, mission: Mission) -> None:
        """Add a mission in the NEW state. It becomes eligible next cycle."""
        if mission.mission_id in self._records:
            raise ValueError(f"mission '{mission.mission_id}' already submitted")
        self._records[mission.mission_id] = MissionRecord(mission=mission)

    def cancel(self, mission_id: str) -> None:
        """Cancel a mission. CANCELLED missions never resume."""
        record = self._record(mission_id)
        if self._can(record, MissionStatus.CANCELLED):
            self._transition(record, MissionStatus.CANCELLED)
            if self._active_mission_id == mission_id:
                self._clear_active()

    def pause(self, mission_id: str) -> None:
        """Pause the active mission. Progress and the active goal are retained."""
        record = self._record(mission_id)
        if self._can(record, MissionStatus.PAUSED):
            self._transition(record, MissionStatus.PAUSED)
            if self._active_mission_id == mission_id:
                self._clear_active()

    def resume(self, mission_id: str) -> None:
        """Make a PAUSED mission eligible again. Selection decides if it runs."""
        record = self._record(mission_id)
        if self._can(record, MissionStatus.READY):
            self._transition(record, MissionStatus.READY)

    def complete_goal(self, goal_id: str) -> None:
        """Explicitly mark the active goal completed and advance the mission."""
        record = self._active_record()
        goal = self._active_goal(record)
        if goal is None or goal.goal_id != goal_id:
            return
        record.goal_statuses[goal_id] = GoalStatus.COMPLETED
        record.active_goal_index = None
        record.recompute_progress()
        self._select_active_goal()

    def fail_goal(self, goal_id: str) -> None:
        """Explicitly fail the active goal and apply the failure policy."""
        record = self._active_record()
        goal = self._active_goal(record)
        if goal is None or goal.goal_id != goal_id:
            return
        attempts = record.attempt_counts.get(goal_id, 0) + 1
        record.attempt_counts[goal_id] = attempts
        action = self.failure_policy.decide(record.mission_id, goal_id, attempts)
        if action is FailureAction.RETRY:
            pass  # the goal stays ACTIVE and is attempted again next cycle
        elif action is FailureAction.PAUSE:
            record.goal_statuses[goal_id] = GoalStatus.FAILED
            self.pause(record.mission_id)
        elif action is FailureAction.FAIL_MISSION:
            record.goal_statuses[goal_id] = GoalStatus.FAILED
            if self._can(record, MissionStatus.FAILED):
                self._transition(record, MissionStatus.FAILED)
            self._clear_active()
        elif action is FailureAction.CANCEL_MISSION:
            record.goal_statuses[goal_id] = GoalStatus.FAILED
            if self._can(record, MissionStatus.CANCELLED):
                self._transition(record, MissionStatus.CANCELLED)
            self._clear_active()

    def observe_execution(self, results: List[ModuleResult], state: RobotState) -> None:
        """Observe what execution produced.

        With an automatic constraint evaluator configured, the active goal is
        checked against the current RobotState and completed when satisfied.
        Without one, this is a no-op and completion happens only through the
        explicit API. The two mechanisms never depend on each other.
        """
        record = self._active_record()
        goal = self._active_goal(record)
        if goal is None:
            return
        if self.constraint_evaluator.is_satisfied(goal, state):
            self.complete_goal(goal.goal_id)

    def current_mission(self) -> Optional[Mission]:
        record = self._active_record()
        return record.mission if record is not None else None

    def current_goal(self) -> Optional[Goal]:
        record = self._active_record()
        if record is None or record.active_goal_index is None:
            return None
        return record.goal(record.active_goal_index)

    def execute(self, state: RobotState, context: RuntimeContext) -> MissionContext:
        """Run one cycle of mission selection.

        Returns the MissionContext Planning should see for this cycle.
        """
        self._promote_new_missions()
        self._select_active_mission()
        self._select_active_goal()
        self._sync_state(state)
        return self.current_context()

    def current_context(self) -> MissionContext:
        record = self._active_record()
        if record is None:
            return MissionContext()
        return MissionContext(
            current_mission=record.mission,
            current_goal=self.current_goal(),
            mission_metadata=dict(record.mission.metadata),
        )

    def status(self, mission_id: str) -> Optional[MissionStatus]:
        record = self._records.get(mission_id)
        return record.status if record is not None else None

    def records(self) -> List[MissionRecord]:
        return list(self._records.values())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _record(self, mission_id: str) -> MissionRecord:
        if mission_id not in self._records:
            raise KeyError(f"unknown mission '{mission_id}'")
        return self._records[mission_id]

    def _active_record(self) -> Optional[MissionRecord]:
        if self._active_mission_id is None:
            return None
        return self._records.get(self._active_mission_id)

    def _active_goal(self, record: Optional[MissionRecord]) -> Optional[Goal]:
        if record is None or record.active_goal_index is None:
            return None
        return record.goal(record.active_goal_index)

    def _can(self, record: MissionRecord, target: MissionStatus) -> bool:
        return self.transition_policy.can_transition(record.status, target)

    def _transition(self, record: MissionRecord, target: MissionStatus) -> None:
        record.status = target

    def _promote_new_missions(self) -> None:
        for record in self._records.values():
            if record.status is MissionStatus.NEW and self._can(record, MissionStatus.READY):
                record.status = MissionStatus.READY

    def _select_active_mission(self) -> None:
        selected = self.selection_policy.select(list(self._records.values()))
        if selected is None:
            self._clear_active()
            return

        if self._active_mission_id is not None and self._active_mission_id != selected.mission_id:
            current = self._records[self._active_mission_id]
            if current.status is MissionStatus.ACTIVE and self._can(current, MissionStatus.READY):
                current.status = MissionStatus.READY
            self._active_mission_id = None

        if self._active_mission_id is None:
            if selected.status is MissionStatus.READY and self._can(selected, MissionStatus.ACTIVE):
                selected.status = MissionStatus.ACTIVE
            elif selected.status is MissionStatus.ACTIVE:
                pass
            else:
                return
            self._active_mission_id = selected.mission_id

    def _select_active_goal(self) -> None:
        record = self._active_record()
        if record is None:
            return

        if record.active_goal_index is not None:
            goal = record.goal(record.active_goal_index)
            if goal is None or record.goal_statuses.get(goal.goal_id) is not GoalStatus.ACTIVE:
                record.active_goal_index = None

        if record.active_goal_index is None:
            for index, goal in enumerate(record.mission.goals):
                if record.goal_statuses.get(goal.goal_id, GoalStatus.PENDING) is GoalStatus.PENDING:
                    if self._dependencies_met(record, goal):
                        record.goal_statuses[goal.goal_id] = GoalStatus.ACTIVE
                        record.active_goal_index = index
                        return

        self._check_mission_completion(record)

    def _dependencies_met(self, record: MissionRecord, goal: Goal) -> bool:
        deps = goal.constraints.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
        return all(
            record.goal_statuses.get(dep) is GoalStatus.COMPLETED for dep in deps
        )

    def _check_mission_completion(self, record: MissionRecord) -> None:
        if not record.mission.goals:
            return
        if all(status is GoalStatus.COMPLETED for status in record.goal_statuses.values()):
            if self._can(record, MissionStatus.COMPLETED):
                record.status = MissionStatus.COMPLETED
            self._clear_active()

    def _clear_active(self) -> None:
        record = self._active_record()
        if record is not None:
            self._last_cleared = record
        self._active_mission_id = None

    def _sync_state(self, state: RobotState) -> None:
        record = self._active_record()
        if record is None:
            last = self._last_cleared
            if last is None:
                state.mission_status = "idle"
                state.metadata["mission_id"] = ""
                state.metadata["progress"] = 0.0
                return
            state.mission_status = last.status.value
            state.metadata["mission_id"] = last.mission_id
            state.metadata["progress"] = last.progress
            return
        self._last_cleared = None
        state.mission_status = record.status.value
        state.metadata["mission_id"] = record.mission_id
        state.metadata["progress"] = record.progress
