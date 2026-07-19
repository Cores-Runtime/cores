from __future__ import annotations

import asyncio
import json
import time
from typing import List, Optional, Set

import websockets

from cores.core import (
    Runtime,
    Scheduler,
    DefaultSchedulingPolicy,
    ExecutionLayer,
)
from cores.interfaces import Module, ModuleResult, ModuleStatus
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext
from cores.runtime import WebSocketRuntimeBridge


class CountingModule(Module):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.count = 0

    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        self.count += 1
        return ModuleResult(module_name=self.name, status=ModuleStatus.SUCCESS)


def _wait_for_condition(condition, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


async def _collect_messages(
    uri: str,
    num_messages: int,
    timeout: float = 5.0,
) -> List[dict]:
    messages = []
    try:
        async with websockets.connect(uri, open_timeout=2.0) as ws:
            while len(messages) < num_messages:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    messages.append(json.loads(raw))
                except asyncio.TimeoutError:
                    break
    except Exception:
        pass
    return messages


async def _collect_messages_raw(
    uri: str,
    timeout: float = 3.0,
) -> List[str]:
    messages = []
    try:
        async with websockets.connect(uri, open_timeout=2.0) as ws:
            try:
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    messages.append(str(raw) if isinstance(raw, bytes) else raw)
            except asyncio.TimeoutError:
                pass
    except Exception:
        pass
    return messages


def test_websocket_bridge_server_startup_and_shutdown() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18765)
    bridge.start()

    assert _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    bridge.close()
    assert not bridge._thread.is_alive()


def test_websocket_bridge_client_connects() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18766)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    connected = False

    async def connect():
        nonlocal connected
        try:
            async with websockets.connect(
                "ws://127.0.0.1:18766", open_timeout=2.0
            ):
                connected = True
                await asyncio.sleep(0.1)
        except Exception:
            pass

    asyncio.run(connect())
    assert connected
    bridge.close()


def test_websocket_bridge_snapshot_broadcast_to_client() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18767)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    async def receive_and_verify():
        async with websockets.connect(
            "ws://127.0.0.1:18767", open_timeout=2.0
        ) as ws:
            await asyncio.sleep(0.2)

            runtime.step()

            raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
            msg = json.loads(raw)

            assert msg["version"] == "1.0"
            assert msg["type"] == "runtime_snapshot"
            assert msg["payload"]["scheduler"]["cycle_count"] == 1
            assert msg["payload"]["robot"]["battery_level"] == 1.0
            assert len(msg["payload"]["modules"]) == 1

    asyncio.run(receive_and_verify())
    bridge.close()


def test_websocket_bridge_multiple_clients() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18768, max_queue_size=5)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    async def connect_and_collect(client_id: int, results: List[str]):
        try:
            async with websockets.connect(
                "ws://127.0.0.1:18768", open_timeout=2.0
            ) as ws:
                await asyncio.sleep(0.3)
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                results.append(raw)
        except Exception as e:
            results.append(f"error_{client_id}:{e}")

    results: List[str] = []

    async def run_test():
        task1 = asyncio.create_task(connect_and_collect(1, results))
        task2 = asyncio.create_task(connect_and_collect(2, results))
        await asyncio.sleep(0.5)
        runtime.step()
        await asyncio.wait_for(asyncio.gather(task1, task2), timeout=5.0)

    asyncio.run(run_test())
    assert len(results) == 2

    for raw in results:
        msg = json.loads(raw)
        assert msg["type"] == "runtime_snapshot"
        assert msg["payload"]["scheduler"]["cycle_count"] == 1

    bridge.close()


def test_websocket_bridge_no_clients_continues() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18769)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    for _ in range(5):
        runtime.step()

    assert runtime.context.cycle_count == 5
    bridge.close()


def test_websocket_bridge_client_reconnect() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18770, max_queue_size=5)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    async def connect_disconnect_reconnect():
        async with websockets.connect(
            "ws://127.0.0.1:18770", open_timeout=2.0
        ) as ws:
            await asyncio.sleep(0.2)
            runtime.step()
            raw1 = await asyncio.wait_for(ws.recv(), timeout=3.0)
            msg1 = json.loads(raw1)
            assert msg1["payload"]["scheduler"]["cycle_count"] == 1

        await asyncio.sleep(0.1)

        async with websockets.connect(
            "ws://127.0.0.1:18770", open_timeout=2.0
        ) as ws2:
            await asyncio.sleep(0.2)
            runtime.step()
            raw2 = await asyncio.wait_for(ws2.recv(), timeout=3.0)
            msg2 = json.loads(raw2)
            assert msg2["payload"]["scheduler"]["cycle_count"] == 2

    asyncio.run(connect_disconnect_reconnect())
    bridge.close()


def test_websocket_bridge_runtime_continues_after_transport_failure() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18771)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    runtime.step()
    assert runtime.context.cycle_count == 1

    bridge.close()

    runtime.step()
    runtime.step()
    assert runtime.context.cycle_count == 3


def test_websocket_bridge_envelope_structure() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18772)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    async def check_envelope():
        async with websockets.connect(
            "ws://127.0.0.1:18772", open_timeout=2.0
        ) as ws:
            await asyncio.sleep(0.2)
            runtime.step()
            raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
            msg = json.loads(raw)

            assert "version" in msg
            assert "type" in msg
            assert "payload" in msg
            assert msg["version"] == "1.0"
            assert msg["type"] == "runtime_snapshot"

            payload = msg["payload"]
            assert "timestamp" in payload
            assert "mission" in payload
            assert "modules" in payload
            assert "active_module_names" in payload
            assert "scheduler" in payload
            assert "robot" in payload
            assert "events" in payload
            assert "explainability" in payload

    asyncio.run(check_envelope())
    bridge.close()


def test_websocket_bridge_queue_drops_stale_snapshots() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18773, max_queue_size=1)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    runtime.step()
    runtime.step()
    runtime.step()
    runtime.step()
    runtime.step()

    assert runtime.bridge.snapshot() is not None
    assert runtime.bridge.snapshot().scheduler.cycle_count == 5
    bridge.close()


def test_websocket_bridge_snapshot_method() -> None:
    bridge = WebSocketRuntimeBridge(host="127.0.0.1", port=18774)
    bridge.start()

    _wait_for_condition(
        lambda: bridge._server is not None and bridge._server.sockets is not None
    )

    scheduler = Scheduler(DefaultSchedulingPolicy())
    execution_layer = ExecutionLayer()
    runtime = Runtime(scheduler, execution_layer, bridge=bridge)
    runtime.register_module(CountingModule("m1"))

    assert bridge.snapshot() is None

    runtime.step()
    snap = bridge.snapshot()
    assert snap is not None
    assert snap.scheduler.cycle_count == 1

    bridge.close()
    assert bridge.snapshot() is None


def test_websocket_bridge_default_port() -> None:
    bridge = WebSocketRuntimeBridge()
    assert bridge._port == 8765
    assert bridge._host == "127.0.0.1"


def test_websocket_bridge_custom_port() -> None:
    bridge = WebSocketRuntimeBridge(host="0.0.0.0", port=9090)
    assert bridge._host == "0.0.0.0"
    assert bridge._port == 9090
