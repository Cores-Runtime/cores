from typing import Dict, List, Callable
from cores.events.event import Event
from cores.events.event_type import EventType


class EventBus:
    """
    EventBus handles synchronous event distribution within the runtime.

    It serves as the internal communication channel, dispatching events to
    registered subscribers in a deterministic, sequential manner.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Register a callback function to be invoked when an event of event_type is published.

        Args:
            event_type: The type of event to subscribe to.
            callback: The callback function to invoke.

        Raises:
            TypeError: If the callback is not callable or event_type is not an EventType.
        """
        if not isinstance(event_type, EventType):
            raise TypeError("event_type must be an instance of EventType enum.")
        if not callable(callback):
            raise TypeError("Subscriber callback must be callable.")

        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Unregister a callback function from receiving events of event_type.

        Args:
            event_type: The type of event to unsubscribe from.
            callback: The callback function to remove.
        """
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:
        """
        Publish an event to the bus.

        The event is dispatched immediately to all registered subscribers for its
        event type in the order of their subscription.

        Args:
            event: The Event instance to publish.
        """
        subscribers = self._subscribers.get(event.event_type, [])
        for callback in subscribers:
            callback(event)
