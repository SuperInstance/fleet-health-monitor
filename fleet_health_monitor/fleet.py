"""FleetHealth — aggregate fleet-wide status from individual nodes."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .node import HealthStatus, NodeHealth
from .threshold import ThresholdConfig


@dataclass
class FleetSummary:
    """Snapshot of fleet health at a point in time."""

    total: int = 0
    healthy: int = 0
    degraded: int = 0
    unhealthy: int = 0
    unknown: int = 0
    timestamp: float = 0.0

    @property
    def health_ratio(self) -> float:
        """Fraction of nodes that are healthy (0.0 – 1.0)."""
        return self.healthy / self.total if self.total else 0.0


class FleetHealth:
    """Manages health state for a collection of nodes.

    Usage::

        fleet = FleetHealth()
        fleet.register(NodeHealth(node_id="agent-1"))
        fleet.record_heartbeat("agent-1")
        summary = fleet.summary()
    """

    def __init__(
        self,
        threshold: Optional[ThresholdConfig] = None,
    ) -> None:
        self.threshold = threshold or ThresholdConfig.defaults()
        self._nodes: Dict[str, NodeHealth] = {}

    # ── node management ──────────────────────────────────────

    def register(self, node: NodeHealth) -> None:
        """Register a new node. Overwrites if node_id already exists."""
        self._nodes[node.node_id] = node

    def unregister(self, node_id: str) -> None:
        """Remove a node from the fleet."""
        self._nodes.pop(node_id, None)

    def get(self, node_id: str) -> Optional[NodeHealth]:
        """Return a node by ID, or None."""
        return self._nodes.get(node_id)

    @property
    def nodes(self) -> Dict[str, NodeHealth]:
        """Read-only view of all nodes."""
        return dict(self._nodes)

    # ── convenience helpers ──────────────────────────────────

    def record_heartbeat(
        self, node_id: str, timestamp: Optional[float] = None
    ) -> None:
        """Record a heartbeat for the given node."""
        node = self._nodes.get(node_id)
        if node is not None:
            node.record_heartbeat(timestamp)

    def record_error(self, node_id: str) -> None:
        """Record an error for the given node."""
        node = self._nodes.get(node_id)
        if node is not None:
            node.record_error()

    # ── evaluation ───────────────────────────────────────────

    def evaluate_node(
        self, node: NodeHealth, now: Optional[float] = None
    ) -> HealthStatus:
        """Determine health status of a single node based on thresholds."""
        now = now or time.time()
        cfg = self.threshold

        elapsed = node.seconds_since_heartbeat(now)

        # Hard failures first
        if node.last_heartbeat == 0.0:
            return HealthStatus.UNKNOWN
        if elapsed >= cfg.heartbeat_timeout:
            return HealthStatus.UNHEALTHY
        if node.cpu_usage is not None and node.cpu_usage >= cfg.cpu_critical:
            return HealthStatus.UNHEALTHY
        if node.memory_usage is not None and node.memory_usage >= cfg.memory_critical:
            return HealthStatus.UNHEALTHY
        if node.error_count >= cfg.error_critical:
            return HealthStatus.UNHEALTHY

        # Warnings
        if elapsed >= cfg.heartbeat_warn:
            return HealthStatus.DEGRADED
        if node.cpu_usage is not None and node.cpu_usage >= cfg.cpu_warn:
            return HealthStatus.DEGRADED
        if node.memory_usage is not None and node.memory_usage >= cfg.memory_warn:
            return HealthStatus.DEGRADED
        if node.error_count >= cfg.error_warn:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def refresh(self, now: Optional[float] = None) -> None:
        """Re-evaluate every node and update their statuses."""
        now = now or time.time()
        for node in self._nodes.values():
            node.status = self.evaluate_node(node, now)

    def summary(self, now: Optional[float] = None) -> FleetSummary:
        """Return a fleet-wide health summary (calls refresh first)."""
        now = now or time.time()
        self.refresh(now)
        counts: Counter[HealthStatus] = Counter()
        for node in self._nodes.values():
            counts[node.status] += 1
        return FleetSummary(
            total=len(self._nodes),
            healthy=counts.get(HealthStatus.HEALTHY, 0),
            degraded=counts.get(HealthStatus.DEGRADED, 0),
            unhealthy=counts.get(HealthStatus.UNHEALTHY, 0),
            unknown=counts.get(HealthStatus.UNKNOWN, 0),
            timestamp=now,
        )
