"""ThresholdConfig — customizable health thresholds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThresholdConfig:
    """Thresholds used to classify node health.

    Attributes:
        heartbeat_timeout: Seconds without a heartbeat before marking UNHEALTHY.
        heartbeat_warn: Seconds without a heartbeat before marking DEGRADED.
        cpu_critical: CPU usage fraction (0-1) for UNHEALTHY.
        cpu_warn: CPU usage fraction (0-1) for DEGRADED.
        memory_critical: Memory usage fraction (0-1) for UNHEALTHY.
        memory_warn: Memory usage fraction (0-1) for DEGRADED.
        error_critical: Error count for UNHEALTHY.
        error_warn: Error count for DEGRADED.
    """

    heartbeat_timeout: float = 60.0
    heartbeat_warn: float = 30.0
    cpu_critical: float = 0.95
    cpu_warn: float = 0.80
    memory_critical: float = 0.95
    memory_warn: float = 0.80
    error_critical: int = 10
    error_warn: int = 5

    @classmethod
    def defaults(cls) -> ThresholdConfig:
        """Return the default configuration."""
        return cls()

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "heartbeat_timeout": self.heartbeat_timeout,
            "heartbeat_warn": self.heartbeat_warn,
            "cpu_critical": self.cpu_critical,
            "cpu_warn": self.cpu_warn,
            "memory_critical": self.memory_critical,
            "memory_warn": self.memory_warn,
            "error_critical": self.error_critical,
            "error_warn": self.error_warn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ThresholdConfig:
        """Deserialize from a plain dict."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
