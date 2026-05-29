# fleet-health-monitor — Fleet Health Daemon

**Continuous health monitoring across the fleet. Node health tracking, threshold alerting, watchdog timers, live dashboards.**

## What This Gives You

- **Node health tracking** — per-agent health status (HEALTHY, DEGRADED, UNHEALTHY, OFFLINE)
- **Threshold configuration** — configurable alert thresholds for response time, error rate, uptime
- **Watchdog timers** — detect stuck or unresponsive agents
- **Fleet aggregation** — roll up individual node health into fleet-wide status
- **Live dashboard** — real-time fleet health visualization

## Quick Start

```bash
pip install fleet-health-monitor
```

```python
from fleet_health_monitor import FleetHealth, NodeHealth, Watchdog, ThresholdConfig

# Configure thresholds
thresholds = ThresholdConfig(
    max_response_time_ms=5000,
    max_error_rate=0.1,
    min_uptime_pct=99.0,
)

# Track node health
fleet = FleetHealth()
fleet.register(NodeHealth(agent_id="agent-1", thresholds=thresholds))
fleet.register(NodeHealth(agent_id="agent-2", thresholds=thresholds))

# Record metrics
fleet.record("agent-1", response_time_ms=120, success=True)
fleet.record("agent-2", response_time_ms=8500, success=False)

# Check fleet status
status = fleet.status()
print(status.healthy)    # 1
print(status.degraded)   # 1
print(status.overall)    # DEGRADED

# Start watchdog
watchdog = Watchdog(fleet=fleet, check_interval_seconds=30)
watchdog.start()
```

## API Reference

### `NodeHealth(agent_id, thresholds)` — `record(response_time_ms, success)`, `status`
### `HealthStatus` — HEALTHY, DEGRADED, UNHEALTHY, OFFLINE
### `ThresholdConfig` — `max_response_time_ms`, `max_error_rate`, `min_uptime_pct`
### `FleetHealth` — `register(node)`, `record(agent_id, ...)`, `status() → FleetStatus`
### `Watchdog(fleet, check_interval_seconds)` — Continuous monitoring loop
### `FleetDashboard` — Real-time visualization

## How It Fits
- [OpenConstruct Documentation](https://github.com/SuperInstance/openconstruct-docs) — ecosystem-wide docs and guides

The system-level health daemon for the [SuperInstance fleet](https://github.com/SuperInstance). Complements [agent-therapy](https://github.com/SuperInstance/agent-therapy) (behavioral health) with infrastructure-level monitoring.

- **[cocapn-health-rs](https://github.com/SuperInstance/cocapn-health-rs)** — Rust health checker (TCP probing)
- **[agent-therapy](https://github.com/SuperInstance/agent-therapy)** — Behavioral health
- **[cicd-agent](https://github.com/SuperInstance/cicd-agent)** — Triggers health checks post-deploy

## Testing

```bash
pytest tests/
```

## Installation

```bash
pip install fleet-health-monitor
```

Python 3.10+. MIT license.
