"""Comprehensive tests for fleet_health_monitor."""

from __future__ import annotations

import time

import pytest

from fleet_health_monitor import (
    FleetDashboard,
    FleetHealth,
    HealthStatus,
    NodeHealth,
    ThresholdConfig,
    Watchdog,
)


# ── NodeHealth ───────────────────────────────────────────────

class TestNodeHealth:
    def test_defaults(self):
        n = NodeHealth(node_id="a1")
        assert n.status == HealthStatus.UNKNOWN
        assert n.last_heartbeat == 0.0
        assert n.cpu_usage is None
        assert n.error_count == 0

    def test_record_heartbeat(self):
        n = NodeHealth(node_id="a1")
        n.record_heartbeat(timestamp=100.0)
        assert n.last_heartbeat == 100.0
        assert n.status == HealthStatus.HEALTHY

    def test_record_error(self):
        n = NodeHealth(node_id="a1")
        n.record_error()
        n.record_error()
        assert n.error_count == 2

    def test_seconds_since_heartbeat(self):
        n = NodeHealth(node_id="a1")
        n.record_heartbeat(timestamp=100.0)
        assert n.seconds_since_heartbeat(now=130.0) == 30.0

    def test_serialization_roundtrip(self):
        n = NodeHealth(
            node_id="x",
            status=HealthStatus.DEGRADED,
            cpu_usage=0.85,
            memory_usage=0.7,
            error_count=3,
            metadata={"zone": "us-east"},
        )
        d = n.to_dict()
        n2 = NodeHealth.from_dict(d)
        assert n2.node_id == "x"
        assert n2.status == HealthStatus.DEGRADED
        assert n2.cpu_usage == 0.85
        assert n2.metadata == {"zone": "us-east"}


# ── ThresholdConfig ──────────────────────────────────────────

class TestThresholdConfig:
    def test_defaults(self):
        cfg = ThresholdConfig.defaults()
        assert cfg.heartbeat_timeout == 60.0
        assert cfg.cpu_warn == 0.80

    def test_custom(self):
        cfg = ThresholdConfig(heartbeat_timeout=120.0, error_warn=3)
        assert cfg.heartbeat_timeout == 120.0
        assert cfg.error_warn == 3

    def test_serialization_roundtrip(self):
        cfg = ThresholdConfig(cpu_critical=0.99, memory_warn=0.5)
        d = cfg.to_dict()
        cfg2 = ThresholdConfig.from_dict(d)
        assert cfg2.cpu_critical == 0.99
        assert cfg2.memory_warn == 0.5


# ── FleetHealth ──────────────────────────────────────────────

class TestFleetHealth:
    def _make_fleet(self, **kw) -> FleetHealth:
        return FleetHealth(threshold=ThresholdConfig(**kw))

    def test_register_and_get(self):
        fleet = self._make_fleet()
        n = NodeHealth(node_id="n1")
        fleet.register(n)
        assert fleet.get("n1") is n
        assert fleet.get("missing") is None

    def test_unregister(self):
        fleet = self._make_fleet()
        fleet.register(NodeHealth(node_id="n1"))
        fleet.unregister("n1")
        assert fleet.get("n1") is None

    def test_record_heartbeat_convenience(self):
        fleet = self._make_fleet()
        fleet.register(NodeHealth(node_id="n1"))
        fleet.record_heartbeat("n1", timestamp=50.0)
        assert fleet.get("n1").last_heartbeat == 50.0

    def test_record_error_convenience(self):
        fleet = self._make_fleet()
        fleet.register(NodeHealth(node_id="n1"))
        fleet.record_error("n1")
        assert fleet.get("n1").error_count == 1

    def test_evaluate_healthy(self):
        fleet = self._make_fleet()
        n = NodeHealth(node_id="n1", cpu_usage=0.3, memory_usage=0.4)
        n.record_heartbeat(timestamp=100.0)
        assert fleet.evaluate_node(n, now=110.0) == HealthStatus.HEALTHY

    def test_evaluate_unknown_no_heartbeat(self):
        fleet = self._make_fleet()
        n = NodeHealth(node_id="n1")
        assert fleet.evaluate_node(n, now=10.0) == HealthStatus.UNKNOWN

    def test_evaluate_unhealthy_timeout(self):
        fleet = self._make_fleet(heartbeat_timeout=60.0)
        n = NodeHealth(node_id="n1")
        n.record_heartbeat(timestamp=100.0)
        assert fleet.evaluate_node(n, now=200.0) == HealthStatus.UNHEALTHY

    def test_evaluate_degraded_heartbeat(self):
        fleet = self._make_fleet(heartbeat_warn=30.0, heartbeat_timeout=60.0)
        n = NodeHealth(node_id="n1")
        n.record_heartbeat(timestamp=100.0)
        assert fleet.evaluate_node(n, now=135.0) == HealthStatus.DEGRADED

    def test_evaluate_unhealthy_cpu(self):
        fleet = self._make_fleet()
        n = NodeHealth(node_id="n1", cpu_usage=0.97)
        n.record_heartbeat(timestamp=0.0)
        assert fleet.evaluate_node(n, now=1.0) == HealthStatus.UNHEALTHY

    def test_evaluate_degraded_cpu(self):
        fleet = self._make_fleet()
        n = NodeHealth(node_id="n1", cpu_usage=0.82)
        n.record_heartbeat(timestamp=0.0)
        assert fleet.evaluate_node(n, now=1.0) == HealthStatus.DEGRADED

    def test_evaluate_unhealthy_errors(self):
        fleet = self._make_fleet()
        n = NodeHealth(node_id="n1", error_count=12)
        n.record_heartbeat(timestamp=0.0)
        assert fleet.evaluate_node(n, now=1.0) == HealthStatus.UNHEALTHY

    def test_evaluate_degraded_errors(self):
        fleet = self._make_fleet()
        n = NodeHealth(node_id="n1", error_count=6)
        n.record_heartbeat(timestamp=0.0)
        assert fleet.evaluate_node(n, now=1.0) == HealthStatus.DEGRADED

    def test_summary_counts(self):
        fleet = self._make_fleet()
        for i in range(3):
            n = NodeHealth(node_id=f"n{i}", cpu_usage=0.1, memory_usage=0.2)
            n.record_heartbeat(timestamp=100.0)
            fleet.register(n)
        fleet.register(NodeHealth(node_id="unknown"))
        s = fleet.summary(now=105.0)
        assert s.total == 4
        assert s.healthy == 3
        assert s.unknown == 1
        assert s.health_ratio == pytest.approx(0.75)

    def test_refresh_updates_statuses(self):
        fleet = self._make_fleet(heartbeat_timeout=10.0)
        n = NodeHealth(node_id="n1")
        n.record_heartbeat(timestamp=100.0)
        fleet.register(n)
        fleet.refresh(now=150.0)
        assert n.status == HealthStatus.UNHEALTHY


# ── Watchdog ─────────────────────────────────────────────────

class TestWatchdog:
    def _make_watchdog(self, **kw) -> tuple[FleetHealth, Watchdog]:
        fleet = FleetHealth(threshold=ThresholdConfig(**kw))
        wd = Watchdog(fleet)
        return fleet, wd

    def test_check_no_change(self):
        fleet, wd = self._make_watchdog()
        n = NodeHealth(node_id="n1")
        n.record_heartbeat(timestamp=0.0)
        n.status = HealthStatus.HEALTHY
        fleet.register(n)
        events = wd.check(now=5.0)
        assert events == []

    def test_check_detects_timeout(self):
        fleet, wd = self._make_watchdog(heartbeat_timeout=10.0)
        n = NodeHealth(node_id="n1")
        n.record_heartbeat(timestamp=100.0)
        n.status = HealthStatus.HEALTHY
        fleet.register(n)
        events = wd.check(now=150.0)
        assert len(events) == 1
        assert events[0].new_status == HealthStatus.UNHEALTHY
        assert events[0].old_status == HealthStatus.HEALTHY
        assert events[0].node_id == "n1"

    def test_callback_fires(self):
        fleet, wd = self._make_watchdog(heartbeat_timeout=10.0)
        collected: list = []
        wd.add_callback(collected.extend)
        n = NodeHealth(node_id="n1")
        n.record_heartbeat(timestamp=100.0)
        n.status = HealthStatus.HEALTHY
        fleet.register(n)
        wd.check(now=150.0)
        assert len(collected) == 1

    def test_remove_callback(self):
        fleet, wd = self._make_watchdog()
        cb = lambda ev: None
        wd.add_callback(cb)
        wd.remove_callback(cb)
        assert len(wd._callbacks) == 0

    def test_events_accumulate(self):
        fleet, wd = self._make_watchdog(heartbeat_timeout=5.0)
        n = NodeHealth(node_id="n1")
        n.record_heartbeat(timestamp=100.0)
        n.status = HealthStatus.HEALTHY
        fleet.register(n)
        wd.check(now=110.0)
        wd.check(now=110.0)  # second check, no new change
        assert len(wd.events) == 1

    def test_clear_events(self):
        fleet, wd = self._make_watchdog()
        wd.clear_events()
        assert wd.events == []


# ── FleetDashboard ───────────────────────────────────────────

class TestFleetDashboard:
    def _make_dashboard(self, **kw) -> tuple[FleetHealth, FleetDashboard]:
        fleet = FleetHealth(threshold=ThresholdConfig(**kw))
        dash = FleetDashboard(fleet, use_unicode=False)
        return fleet, dash

    def test_render_summary(self):
        fleet, dash = self._make_dashboard()
        n = NodeHealth(node_id="a1", cpu_usage=0.1, memory_usage=0.2)
        n.record_heartbeat(timestamp=100.0)
        fleet.register(n)
        text = dash.render_summary(now=105.0)
        assert "1 nodes" in text
        assert "1 healthy" in text

    def test_render_table(self):
        fleet, dash = self._make_dashboard()
        n = NodeHealth(node_id="a1", cpu_usage=0.5, memory_usage=0.6)
        n.record_heartbeat(timestamp=100.0)
        fleet.register(n)
        text = dash.render_table(now=105.0)
        assert "FLEET HEALTH DASHBOARD" in text
        assert "a1" in text

    def test_render_empty_fleet(self):
        fleet, dash = self._make_dashboard()
        text = dash.render_summary(now=100.0)
        assert "0 nodes" in text
        assert "0% healthy" in text

    def test_unicode_mode(self):
        fleet = FleetHealth()
        dash = FleetDashboard(fleet, use_unicode=True)
        n = NodeHealth(node_id="x")
        n.record_heartbeat(timestamp=0.0)
        fleet.register(n)
        text = dash.render_table(now=5.0)
        # Should contain a Unicode icon
        assert any(c in text for c in "🟢🟡🔴⚪")


# ── Integration ──────────────────────────────────────────────

class TestIntegration:
    def test_full_workflow(self):
        """Register nodes, degrade one, check watchdog fires, render."""
        fleet = FleetHealth(threshold=ThresholdConfig(
            heartbeat_timeout=60.0, heartbeat_warn=30.0,
        ))
        wd = Watchdog(fleet)
        events_log: list = []
        wd.add_callback(events_log.extend)
        dash = FleetDashboard(fleet, use_unicode=False)

        # Register 3 nodes
        for i in range(3):
            n = NodeHealth(node_id=f"agent-{i}", cpu_usage=0.2, memory_usage=0.3)
            n.record_heartbeat(timestamp=100.0)
            fleet.register(n)

        # Initial check — all healthy
        events = wd.check(now=110.0)
        assert len(events) == 0  # statuses set by evaluate, not changed

        summary = fleet.summary(now=110.0)
        assert summary.healthy == 3

        # Time passes — nodes timeout
        events = wd.check(now=180.0)
        assert len(events) == 3
        for e in events:
            assert e.new_status == HealthStatus.UNHEALTHY

        # Dashboard renders
        text = dash.render_table(now=180.0)
        assert "CRIT" in text
        assert "agent-0" in text
