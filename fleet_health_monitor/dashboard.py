"""FleetDashboard — ASCII status display for the fleet."""

from __future__ import annotations

from typing import Optional

from .fleet import FleetHealth, FleetSummary
from .node import HealthStatus


_STATUS_ICONS: dict[HealthStatus, str] = {
    HealthStatus.HEALTHY: "🟢",
    HealthStatus.DEGRADED: "🟡",
    HealthStatus.UNHEALTHY: "🔴",
    HealthStatus.UNKNOWN: "⚪",
}

_STATUS_ASCII: dict[HealthStatus, str] = {
    HealthStatus.HEALTHY: "[OK]",
    HealthStatus.DEGRADED: "[WARN]",
    HealthStatus.UNHEALTHY: "[CRIT]",
    HealthStatus.UNKNOWN: "[???]",
}


class FleetDashboard:
    """Generates ASCII (or Unicode) status displays for a fleet."""

    def __init__(self, fleet: FleetHealth, use_unicode: bool = True) -> None:
        self.fleet = fleet
        self.use_unicode = use_unicode

    def _icon(self, status: HealthStatus) -> str:
        return _STATUS_ICONS[status] if self.use_unicode else _STATUS_ASCII[status]

    # ── rendering ────────────────────────────────────────────

    def render_summary(self, now: Optional[float] = None) -> str:
        """Render a one-line fleet summary."""
        summary = self.fleet.summary(now)
        pct = summary.health_ratio * 100
        return (
            f"Fleet: {summary.total} nodes | "
            f"{summary.healthy} healthy, "
            f"{summary.degraded} degraded, "
            f"{summary.unhealthy} unhealthy, "
            f"{summary.unknown} unknown | "
            f"{pct:.0f}% healthy"
        )

    def render_table(self, now: Optional[float] = None) -> str:
        """Render a full ASCII table of all nodes."""
        summary = self.fleet.summary(now)
        lines: list[str] = []

        # Header
        lines.append("=" * 60)
        lines.append("  FLEET HEALTH DASHBOARD")
        lines.append("=" * 60)
        lines.append(
            f"  Total: {summary.total}  "
            f"Healthy: {summary.healthy}  "
            f"Degraded: {summary.degraded}  "
            f"Unhealthy: {summary.unhealthy}"
        )
        lines.append("-" * 60)
        lines.append(f"  {'ID':<20s} {'STATUS':<10s} {'CPU':>6s} {'MEM':>6s} {'ERRS':>5s}")
        lines.append("-" * 60)

        for node in sorted(self.fleet.nodes.values(), key=lambda n: n.node_id):
            icon = self._icon(node.status)
            cpu = f"{node.cpu_usage:.0%}" if node.cpu_usage is not None else "  -  "
            mem = f"{node.memory_usage:.0%}" if node.memory_usage is not None else "  -  "
            lines.append(
                f"  {icon} {node.node_id:<17s} {node.status.value:<10s} "
                f"{cpu:>6s} {mem:>6s} {node.error_count:>5d}"
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def render(self, now: Optional[float] = None) -> str:
        """Render the full dashboard (alias for render_table)."""
        return self.render_table(now)
