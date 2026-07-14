import asyncio
from typing import Dict, List, Callable, Awaitable
from cores.events import Event

class EventBus:
    """
    EventBus handles asynchronous event distribution within the runtime.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self._history: List[Event] = []

    def subscribe(self, event_type: str, callback: Callable[[Event], Awaitable[None]]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, event: Event):
        self._history.append(event)
        subscribers = self._subscribers.get(event.event_type, [])
        if subscribers:
            await asyncio.gather(*(callback(event) for callback in subscribers))

    def get_history(self) -> List[Event]:
        return self._history.copy()
