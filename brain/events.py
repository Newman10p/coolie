"""Append-only, in-process event recording and explicit subscriber delivery."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from threading import RLock
from typing import Any
import secrets

from .models import BrainEvent, DataSensitivity


class EventBus:
    def __init__(self, persistence=None) -> None:
        self._persistence = persistence
        self._events: list[BrainEvent] = (
            []
            if persistence is None
            else list(persistence.events("brain_events", BrainEvent))
        )
        self._subscribers: dict[str, list[tuple[str, Callable[[BrainEvent], None]]]] = {}
        self._acknowledged: set[tuple[str, str]] = set()
        self._in_flight: set[tuple[str, str]] = set()
        self._lock = RLock()

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[BrainEvent], None],
        *,
        subscriber_id: str | None = None,
    ) -> str:
        if not event_type.strip() or not callable(handler):
            raise ValueError("event_type and a callable handler are required.")
        identifier = subscriber_id or secrets.token_urlsafe(12)
        if not identifier.strip():
            raise ValueError("subscriber_id is required.")
        with self._lock:
            subscribers = self._subscribers.setdefault(event_type, [])
            if any(existing_id == identifier for existing_id, _ in subscribers):
                raise ValueError(f"Subscriber already registered: {identifier}")
            subscribers.append((identifier, handler))
        return identifier

    def publish(
        self,
        event_type: str,
        *,
        source: str,
        payload: dict[str, Any],
        correlation_id: str,
        sensitivity: DataSensitivity = DataSensitivity.INTERNAL,
    ) -> BrainEvent:
        if not event_type.strip() or not source.strip() or not correlation_id.strip():
            raise ValueError("Event type, source, and correlation_id are required.")
        event = BrainEvent(secrets.token_urlsafe(18), event_type, source, deepcopy(payload), correlation_id, sensitivity)
        with self._lock:
            if self._persistence is not None:
                self._persistence.append_event(
                    "brain_events", event_type, event.event_id, event
                )
            self._events.append(event)
        return deepcopy(event)

    def dispatch(self, event_id: str) -> None:
        with self._lock:
            event = next((item for item in self._events if item.event_id == event_id), None)
            if event is None:
                raise KeyError(f"Unknown event: {event_id}")
            handlers = tuple(self._subscribers.get(event.event_type, ()))
        for subscriber_id, handler in handlers:
            delivery = event_id, subscriber_id
            with self._lock:
                if delivery in self._acknowledged or delivery in self._in_flight:
                    continue
                self._in_flight.add(delivery)
            delivered = False
            try:
                handler(deepcopy(event))
                delivered = True
            finally:
                with self._lock:
                    self._in_flight.remove(delivery)
                    if delivered:
                        self._acknowledged.add(delivery)

    def events(self, *, event_type: str | None = None) -> tuple[BrainEvent, ...]:
        with self._lock:
            return tuple(
                deepcopy(event) for event in self._events if event_type is None or event.event_type == event_type
            )
