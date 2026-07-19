from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
from typing import Optional, Set

import websockets.asyncio.server as ws_server

from cores.runtime.runtime_bridge import RuntimeBridge
from cores.runtime.runtime_state import RuntimeState

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "1.0"


def _wrap_snapshot(snapshot: RuntimeState) -> str:
    raw = snapshot.model_dump_json()
    envelope = {
        "version": PROTOCOL_VERSION,
        "type": "runtime_snapshot",
        "payload": json.loads(raw),
    }
    return json.dumps(envelope)


class WebSocketRuntimeBridge(RuntimeBridge):
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        max_queue_size: int = 1,
    ) -> None:
        self._host = host
        self._port = port
        self._max_queue_size = max_queue_size

        self._latest_snapshot: Optional[RuntimeState] = None
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)

        self._server: Optional[ws_server.Server] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._clients: Set[ws_server.ServerConnection] = set()
        self._lock: threading.Lock = threading.Lock()
        self._started = False
        self._stopped = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._stopped = False
        self._thread = threading.Thread(
            target=self._run_event_loop,
            name="cores-ws-bridge",
            daemon=True,
        )
        self._thread.start()

    def publish(self, state: RuntimeState) -> None:
        self._latest_snapshot = state
        try:
            self._queue.put_nowait(state)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(state)
            except queue.Empty:
                pass

    def snapshot(self) -> Optional[RuntimeState]:
        return self._latest_snapshot

    def subscribe(self, callback) -> None:
        pass

    def close(self) -> None:
        self._stopped = True
        if self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._do_close)

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        with self._lock:
            self._clients.clear()
        self._latest_snapshot = None

    def _do_close(self) -> None:
        if self._server is not None:
            self._server.close()
        asyncio.get_running_loop().stop()

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception:
            logger.exception("WebSocket bridge event loop exited with error")
        finally:
            try:
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception:
                pass
            self._loop.close()

    async def _serve(self) -> None:
        try:
            self._server = await ws_server.serve(
                self._handle_client,
                host=self._host,
                port=self._port,
                reuse_address=True,
                reuse_port=False,
            )
            logger.info(
                "WebSocket bridge listening on ws://%s:%d",
                self._host,
                self._port,
            )
            await self._broadcast_loop()
        except OSError as exc:
            logger.error("WebSocket bridge failed to start on %s:%d: %s", self._host, self._port, exc)

    async def _broadcast_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._stopped:
            try:
                snapshot = await loop.run_in_executor(None, self._queue.get)
            except Exception:
                if not self._stopped:
                    logger.exception("WebSocket bridge queue read error")
                break

            if self._stopped:
                break

            try:
                message = _wrap_snapshot(snapshot)
            except Exception:
                logger.exception("WebSocket bridge serialization error")
                continue

            await self._broadcast(message)

    async def _broadcast(self, message: str) -> None:
        with self._lock:
            clients = list(self._clients)

        if not clients:
            return

        stale: list[ws_server.ServerConnection] = []
        for ws in clients:
            try:
                await ws.send(message)
            except websockets.ConnectionClosed:
                stale.append(ws)
            except Exception:
                logger.exception("WebSocket bridge broadcast error")
                stale.append(ws)

        if stale:
            with self._lock:
                for ws in stale:
                    self._clients.discard(ws)
            logger.debug("WebSocket bridge removed %d stale client(s)", len(stale))

    async def _handle_client(self, ws: ws_server.ServerConnection) -> None:
        with self._lock:
            self._clients.add(ws)
        logger.debug("WebSocket client connected (%d total)", len(self._clients))
        try:
            async for _ in ws:
                pass
        except websockets.ConnectionClosed:
            pass
        except Exception:
            logger.exception("WebSocket client handler error")
        finally:
            with self._lock:
                self._clients.discard(ws)
            logger.debug("WebSocket client disconnected (%d remaining)", len(self._clients))
