"""NodeHealth — track individual agent health."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HealthStatus(Enum):
    """Possible health states for a node."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class NodeHealth:
    """Represents the health state of a single agent node.

    Attributes:
        node_id: Unique identifier for this node.
        status: Current health status.
        last_heartbeat: Timestamp of the last heartbeat received.
        cpu_usage: CPU utilization (0.0 – 1.0), or None if unknown.
        memory_usage: Memory utilization (0.0 – 1.0), or None if unknown.
        error_count: Number of recent errors.
        metadata: Arbitrary key-value metadata.
    """

    node_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_heartbeat: float = 0.0
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    error_count: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    # ── helpers ──────────────────────────────────────────────

    def record_heartbeat(self, timestamp: Optional[float] = None) -> None:
        """Record a heartbeat at *timestamp* (defaults to now)."""
        self.last_heartbeat = timestamp or time.time()
        if self.status == HealthStatus.UNKNOWN:
            self.status = HealthStatus.HEALTHY

    def record_error(self) -> None:
        """Increment the error counter."""
        self.error_count += 1

    def seconds_since_heartbeat(self, now: Optional[float] = None) -> float:
        """Return seconds elapsed since the last heartbeat."""
        base = now or time.time()
        return base - self.last_heartbeat

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "error_count": self.error_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NodeHealth:
        """Deserialize from a plain dict."""
        data = dict(data)  # shallow copy
        if "status" in data and isinstance(data["status"], str):
            data["status"] = HealthStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
