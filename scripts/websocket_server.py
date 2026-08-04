"""Stream a live CORES Runtime over WebSocket for the replay simulator.

Builds the same Mars rover scenario as the trace recorder, but publishes
every RuntimeState snapshot to WebSocket clients through the
WebSocketRuntimeBridge instead of writing a trace file. The cycle loop is
paced so snapshots reach the 3D scene at a watchable speed.

Run:  uv run python scripts/websocket_server.py [--delay 0.5] [--port 8765]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from record_runtime_trace import N_CYCLES, build_runtime, scenario_events
from cores.runtime.websocket_bridge import WebSocketRuntimeBridge

logger = logging.getLogger("websocket_server")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", type=int, default=8765, help="bind port")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="wall-clock seconds between runtime cycles",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    bridge = WebSocketRuntimeBridge(host=args.host, port=args.port)
    runtime, _, _ = build_runtime(bridge)
    bridge.start()

    try:
        for cycle in range(N_CYCLES):
            for event in scenario_events(cycle):
                runtime.event_bus.publish(event)
            runtime.step()
            if args.delay > 0:
                time.sleep(args.delay)
            if cycle % 10 == 0:
                logger.info("cycle %d/%d", cycle, N_CYCLES)
        logger.info("scenario complete after %d cycles", N_CYCLES)
    except KeyboardInterrupt:
        logger.info("interrupted by user")
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
