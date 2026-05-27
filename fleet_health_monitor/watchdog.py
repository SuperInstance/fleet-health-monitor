"""Watchdog — periodic health checks with timeout detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .fleet import FleetHealth
from .node import HealthStatus, NodeHealth
from .threshold import ThresholdConfig


@dataclass
class WatchdogEvent:
    """An event emitted by the watchdog."""

    timestamp: float
    node_id: str
    old_status: HealthStatus
    new_status: HealthStatus
    message: str


class Watchdog:
    """Monitors a fleet and detects state transitions.

    Callbacks receive a list of :class:`WatchdogEvent` on every check.
    """

    def __init__(
        self,
        fleet: FleetHealth,
        check_interval: float = 10.0,
        callbacks: Optional[List[Callable[[List[WatchdogEvent]], None]]] = None,
    ) -> None:
        self.fleet = fleet
        self.check_interval = check_interval
        self._callbacks: List[Callable[[List[WatchdogEvent]], None]] = list(
            callbacks or []
        )
        self._last_check: float = 0.0
        self._events: List[WatchdogEvent] = []
        self._running = False

    # ── callback management ──────────────────────────────────

    def add_callback(self, cb: Callable[[List[WatchdogEvent]], None]) -> None:
        """Register a callback to fire on health changes."""
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[List[WatchdogEvent]], None]) -> None:
        """Remove a previously registered callback."""
        self._callbacks = [c for c in self._callbacks if c is not cb]

    # ── checking ─────────────────────────────────────────────

    def check(self, now: Optional[float] = None) -> List[WatchdogEvent]:
        """Run one health check, returning any status-change events."""
        now = now or time.time()
        events: List[WatchdogEvent] = []

        for node_id, node in list(self.fleet.nodes.items()):
            old_status = node.status
            new_status = self.fleet.evaluate_node(node, now)
            node.status = new_status

            if new_status != old_status:
                event = WatchdogEvent(
                    timestamp=now,
                    node_id=node_id,
                    old_status=old_status,
                    new_status=new_status,
                    message=self._describe(old_status, new_status, node),
                )
                events.append(event)
                self._events.append(event)

        if events:
            for cb in self._callbacks:
                cb(events)

        self._last_check = now
        return events

    # ── history ──────────────────────────────────────────────

    @property
    def events(self) -> List[WatchdogEvent]:
        """All events accumulated so far."""
        return list(self._events)

    @property
    def last_check_time(self) -> float:
        """Timestamp of the most recent check."""
        return self._last_check

    def clear_events(self) -> None:
        """Clear stored events."""
        self._events.clear()

    # ── internal ─────────────────────────────────────────────

    @staticmethod
    def _describe(
        old: HealthStatus, new: HealthStatus, node: NodeHealth
    ) -> str:
        return f"{node.node_id}: {old.value} → {new.value}"
