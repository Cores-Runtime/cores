from pytest import approx
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.core.memory import Memory, MemoryRecord, MemoryType, MemoryQuery
from cores.core.memory.types import NarrativeRecord


def _memory_with_outcomes(
    outcomes, cycles=None, narratives=()
) -> Memory:
    mem = Memory()
    for i, outcome in enumerate(outcomes):
        action, result = outcome
        mem.store(
            MemoryRecord(
                id=f"out_{i}",
                content={"action": action, "result": result},
                cycle=cycles[i] if cycles else i + 1,
                importance=0.8,
                record_type=MemoryType.OUTCOME,
            )
        )
    for i, narrative in enumerate(narratives):
        mem.semantic.store_narrative(narrative)
    mem.execute(RobotState(), RuntimeContext(cycle_count=0))
    return mem


class TestMemoryEvidence:
    def test_empty_memory(self):
        mem = Memory()
        evidence = mem.evidence()
        assert evidence.failures == ()
        assert evidence.successes == ()
        assert evidence.narratives == ()

    def test_failure_evidence_aggregation(self):
        mem = _memory_with_outcomes(
            [
                ("open_door_a", "FAILURE"),
                ("open_door_a", "FAILURE"),
                ("open_door_b", "SUCCESS"),
            ],
            cycles=[1, 3, 2],
        )
        evidence = mem.evidence()
        assert evidence.failure_count("open_door_a") == 2
        assert evidence.failure_count("open_door_b") == 0
        assert evidence.success_count("open_door_b") == 1

        failure = evidence.failures[0]
        assert failure.action == "open_door_a"
        assert failure.count == 2
        assert failure.latest_cycle == 3
        assert failure.mean_importance == approx(0.8)

        success = evidence.successes[0]
        assert success.action == "open_door_b"
        assert success.count == 1
        assert success.latest_cycle == 2

    def test_skipped_outcomes_not_evidence(self):
        mem = _memory_with_outcomes([("idle", "SKIPPED")])
        evidence = mem.evidence()
        assert evidence.failure_count("idle") == 0
        assert evidence.success_count("idle") == 0

    def test_narrative_evidence(self):
        mem = Memory()
        mem.semantic.store_narrative(
            NarrativeRecord(
                id="n1",
                content={"summary": "door_a route blocked"},
                cycle=1,
                confidence=0.7,
                topic="route_door_a",
            )
        )
        mem.semantic.store_narrative(
            NarrativeRecord(
                id="n2",
                content={"summary": "door_a still blocked"},
                cycle=2,
                confidence=0.9,
                topic="route_door_a",
            )
        )
        evidence = mem.evidence()
        narr = evidence.narrative_for_topic("route_door_a")
        assert narr is not None
        assert narr.count == 2
        assert narr.confidence == 0.9

    def test_plan_records_not_counted_as_outcomes(self):
        mem = Memory()
        mem.store(
            MemoryRecord(
                id="plan_1",
                content={"plan_id": "p1", "actions": ["open_door_a"]},
                cycle=1,
                record_type=MemoryType.PLAN,
            )
        )
        mem.execute(RobotState(), RuntimeContext(cycle_count=0))
        evidence = mem.evidence()
        assert evidence.failure_count("open_door_a") == 0
        assert evidence.success_count("open_door_a") == 0

    def test_action_query_filters(self):
        mem = _memory_with_outcomes(
            [
                ("open_door_a", "FAILURE"),
                ("open_door_b", "FAILURE"),
            ],
            cycles=[1, 2],
        )
        evidence = mem.evidence(MemoryQuery(action="open_door_a"))
        assert evidence.failure_count("open_door_a") == 1
        assert evidence.failure_count("open_door_b") == 0

    def test_evidence_is_deterministic(self):
        outcomes = [
            ("open_door_b", "FAILURE"),
            ("open_door_a", "SUCCESS"),
        ]
        e1 = _memory_with_outcomes(outcomes, cycles=[1, 2]).evidence()
        e2 = _memory_with_outcomes(outcomes, cycles=[1, 2]).evidence()
        assert e1 == e2
