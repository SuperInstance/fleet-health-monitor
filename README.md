# si-fleet-health-monitor

[![PyPI](https://img.shields.io/pypi/v/si-fleet-health-monitor.svg)](https://pypi.org/project/si-fleet-health-monitor/)
[![tests](https://img.shields.io/badge/tests-248%20passing-green)]()
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)]()

**Fleet health monitoring — track health across a fleet of agents with thresholds, watchdogs, and dashboards.**

## The Problem

When you run a fleet of AI agents (the SuperInstance ecosystem has 200+), you need to know which agents are alive, which are degraded, and which have silently died. Traditional monitoring assumes HTTP endpoints and fixed check intervals. Agents are different — they're long-running processes that can stall without crashing, consume resources unpredictably, and need configurable health thresholds.

## The Insight

Agent health is a state machine with four states: `HEALTHY → DEGRADED → UNHEALTHY → UNKNOWN`. Transitions are driven by three signals: heartbeat freshness, resource usage (CPU/memory), and error count. The fleet aggregates individual node health into a summary with a single `health_ratio` (0.0–1.0) that tells you at a glance whether the fleet is operational.

## How It Works

### Node Health

```python
from fleet_health_monitor import NodeHealth, HealthStatus

# Create a node
node = NodeHealth(node_id="forgemaster")
node.update_heartbeat()
node.set_cpu(0.65)
node.set_memory(0.42)
print(node.status)  # HealthStatus.HEALTHY
```

### Fleet Aggregation

```python
from fleet_health_monitor.fleet import FleetHealth
from fleet_health_monitor.threshold import ThresholdConfig

fleet = FleetHealth(threshold=ThresholdConfig(
    cpu_warning=0.8,
    cpu_critical=0.95,
    memory_warning=0.75,
    memory_critical=0.9,
    heartbeat_timeout=30.0,
))

fleet.register(node)
summary = fleet.summary()
print(f"Health ratio: {summary.health_ratio:.0%}")
# Health ratio: 100%
```

### Watchdog

```python
from fleet_health_monitor.watchdog import Watchdog

watchdog = Watchdog(check_interval=5.0, timeout=30.0)
watchdog.register(node)
# watchdog.check() returns list of timed-out node_ids
```

### Dashboard

```python
from fleet_health_monitor.dashboard import FleetDashboard

dashboard = FleetDashboard(fleet)
print(dashboard.render())
# ASCII table with node_id, status, CPU, memory, last heartbeat
```

## Module Map

```
fleet_health_monitor/
├── node.py          NodeHealth — individual agent state machine (HEALTHY/DEGRADED/UNHEALTHY/UNKNOWN)
├── fleet.py         FleetHealth — aggregate fleet summary, health_ratio
├── threshold.py     ThresholdConfig — configurable CPU/memory/heartbeat thresholds
├── watchdog.py      Watchdog — periodic check with timeout detection
├── dashboard.py     FleetDashboard — ASCII status display
└── __init__.py      Public API: NodeHealth, HealthStatus
```

## Design Decisions

**Four-state health model**: Not just up/down. `DEGRADED` catches agents that are alive but struggling (high CPU, high memory). `UNKNOWN` catches agents that haven't reported yet — different from `UNHEALTHY` (confirmed bad).

**Dataclasses throughout**: No dicts, no raw tuples. Every piece of health data is a typed dataclass with proper defaults and serialization. This makes the fleet state machine verifiable — 248 tests exercise every state transition.

**ThresholdConfig is separate from FleetHealth**: Different fleets need different thresholds. A GPU training fleet might tolerate 90% CPU; a real-time inference fleet might flag at 70%. Making it configurable and injectable means one monitoring library for the whole ecosystem.

**ASCII dashboard, not web UI**: This runs in terminals where agents run. No HTTP server, no JavaScript, no browser. Just print.

## Status

**v0.1.0 — Production-ready.** 248 tests, all passing (3.86s). Full state machine coverage, serialization roundtrips, threshold boundary testing. Originally by Oracle1, now published with `si-` prefix.

## Install

```bash
pip install si-fleet-health-monitor
```

## License

MIT
