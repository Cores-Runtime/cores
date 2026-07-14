import pytest
from pydantic import ValidationError
from cores.events import EventBus, Event, EventType


def test_event_bus_basic_publish_subscribe() -> None:
    """
    Verify that a subscriber receives the published event of the registered type.
    """
    event_bus = EventBus()
    received_events = []

    def callback(event: Event) -> None:
        received_events.append(event)

    event_bus.subscribe(EventType.DIAGNOSTIC, callback)

    event = Event(source="test_source", event_type=EventType.DIAGNOSTIC, payload={"data": 42})
    event_bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0] == event


def test_event_bus_unsubscribe() -> None:
    """
    Verify that unsubscribing a callback stops it from receiving future events.
    """
    event_bus = EventBus()
    received_events = []

    def callback(event: Event) -> None:
        received_events.append(event)

    event_bus.subscribe(EventType.DIAGNOSTIC, callback)

    event = Event(source="test", event_type=EventType.DIAGNOSTIC)
    event_bus.publish(event)
    assert len(received_events) == 1

    event_bus.unsubscribe(EventType.DIAGNOSTIC, callback)
    event_bus.publish(event)
    # Count should still be 1 (second dispatch not received)
    assert len(received_events) == 1


def test_event_bus_multiple_subscribers_order() -> None:
    """
    Verify that multiple subscribers are executed in the exact order they subscribed.
    """
    event_bus = EventBus()
    execution_order = []

    def callback_one(event: Event) -> None:
        execution_order.append(1)

    def callback_two(event: Event) -> None:
        execution_order.append(2)

    event_bus.subscribe(EventType.DIAGNOSTIC, callback_one)
    event_bus.subscribe(EventType.DIAGNOSTIC, callback_two)

    event = Event(source="test_source", event_type=EventType.DIAGNOSTIC)
    event_bus.publish(event)

    assert execution_order == [1, 2]


def test_event_bus_routing() -> None:
    """
    Verify that subscribers only receive events of the type they subscribed to.
    """
    event_bus = EventBus()
    received_a = []
    received_b = []

    event_bus.subscribe(EventType.STATE_UPDATED, lambda e: received_a.append(e))
    event_bus.subscribe(EventType.SYSTEM_EMERGENCY, lambda e: received_b.append(e))

    event_a = Event(source="test", event_type=EventType.STATE_UPDATED)
    event_b = Event(source="test", event_type=EventType.SYSTEM_EMERGENCY)

    event_bus.publish(event_a)
    assert len(received_a) == 1
    assert len(received_b) == 0

    event_bus.publish(event_b)
    assert len(received_a) == 1
    assert len(received_b) == 1


def test_event_bus_no_subscribers() -> None:
    """
    Verify publishing an event with no subscribers succeeds without side effects.
    """
    event_bus = EventBus()
    event = Event(source="test", event_type=EventType.DIAGNOSTIC)

    # Should not raise any exceptions
    event_bus.publish(event)


def test_event_bus_invalid_subscription() -> None:
    """
    Verify subscribe raises TypeError if parameters are invalid.
    """
    event_bus = EventBus()

    # Invalid callback
    with pytest.raises(TypeError, match="Subscriber callback must be callable"):
        event_bus.subscribe(EventType.DIAGNOSTIC, "not_a_callback")  # type: ignore

    # Invalid event_type
    with pytest.raises(TypeError, match="event_type must be an instance of EventType enum"):
        event_bus.subscribe("not_an_enum", lambda e: None)  # type: ignore


def test_event_bus_exception_propagation() -> None:
    """
    Verify that exceptions raised in subscribers propagate up to the publisher.
    """
    event_bus = EventBus()

    def buggy_callback(event: Event) -> None:
        raise ValueError("Something went wrong in callback")

    event_bus.subscribe(EventType.DIAGNOSTIC, buggy_callback)
    event = Event(source="test", event_type=EventType.DIAGNOSTIC)

    with pytest.raises(ValueError, match="Something went wrong in callback"):
        event_bus.publish(event)


def test_event_immutability() -> None:
    """
    Verify that Event is immutable (frozen) after creation.
    """
    event = Event(source="test", event_type=EventType.DIAGNOSTIC, payload={"key": "val"})

    with pytest.raises((ValidationError, TypeError)):
        event.source = "new_source"  # type: ignore

    with pytest.raises((ValidationError, TypeError)):
        event.payload = {"new": "payload"}  # type: ignore
