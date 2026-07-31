"""Tests for Narrator trigger policies."""

from cores.core.memory import (
    MemoryRecord,
    MemoryType,
    EpisodicStore,
)
from cores.core.memory.strategies.fifo_memory import FIFOMemoryStrategy
from cores.core.logger.triggers import (
    CapacityTrigger,
    CountTrigger,
    IdleTrigger,
    CompositeTrigger,
)
from cores.core.runtime_context import RuntimeContext


def make_record(rid: str) -> MemoryRecord:
    return MemoryRecord(
        id=rid, content={"x": 1}, cycle=0,
        importance=0.5, record_type=MemoryType.OBSERVATION,
    )


class TestCapacityTrigger:
    def test_below_threshold_returns_false(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        store.store(make_record("r1"))
        store.execute(0)
        trigger = CapacityTrigger(threshold=10)
        ctx = RuntimeContext()
        assert trigger.should_run(store, ctx) is False

    def test_above_threshold_returns_true(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        for i in range(10):
            store.store(make_record(f"r{i}"))
        store.execute(0)
        trigger = CapacityTrigger(threshold=5)
        ctx = RuntimeContext()
        assert trigger.should_run(store, ctx) is True


class TestCountTrigger:
    def test_below_count_returns_false(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        for i in range(3):
            store.store(make_record(f"r{i}"))
        store.execute(0)
        trigger = CountTrigger(count=10)
        ctx = RuntimeContext()
        assert trigger.should_run(store, ctx) is False

    def test_above_count_returns_true(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        for i in range(10):
            store.store(make_record(f"r{i}"))
        store.execute(0)
        trigger = CountTrigger(count=5)
        ctx = RuntimeContext()
        assert trigger.should_run(store, ctx) is True


class TestIdleTrigger:
    def test_not_idle_returns_false(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        trigger = IdleTrigger(idle_cycles=10)
        ctx = RuntimeContext(cycle_count=5)
        assert trigger.should_run(store, ctx) is False

    def test_idle_enough_returns_true(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        trigger = IdleTrigger(idle_cycles=10)
        ctx = RuntimeContext(cycle_count=15)
        assert trigger.should_run(store, ctx) is True


class TestCompositeTrigger:
    def test_any_mode_one_true(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        t1 = CountTrigger(count=1)
        t2 = IdleTrigger(idle_cycles=1000)
        trigger = CompositeTrigger([t1, t2], mode="any")
        store.store(make_record("r1"))
        store.execute(0)
        ctx = RuntimeContext()
        assert trigger.should_run(store, ctx) is True

    def test_all_mode_one_false(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        t1 = CountTrigger(count=1)
        t2 = IdleTrigger(idle_cycles=1000)
        trigger = CompositeTrigger([t1, t2], mode="all")
        store.store(make_record("r1"))
        store.execute(0)
        ctx = RuntimeContext()
        assert trigger.should_run(store, ctx) is False

    def test_no_triggers_returns_false(self):
        store = EpisodicStore(FIFOMemoryStrategy(max_size=100))
        trigger = CompositeTrigger([])
        ctx = RuntimeContext()
        assert trigger.should_run(store, ctx) is False
