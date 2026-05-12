# fleet-health-monitor — Fleet Health Tracking

Oracle1's health monitoring service. 1589 auto-commits from beachcomb cycles.

## What It Does

Continuously monitors the health of all fleet services and agents. Produces `health_report.json` every cycle (~180s).

## Key Output: `data/output/health_report.json`

```json
{
  "timestamp": "2026-05-07T07:30:01Z",
  "services": {
    "plato": {"status": "green", "port": 8847, "latency_ms": 12},
    "nexus": {"status": "green", "port": 4047, "latency_ms": 8},
    "dashboard": {"status": "green", "port": 4046, "latency_ms": 45},
    "gatekeeper": {"status": "green", "port": 4053, "latency_ms": 3},
    "keeper": {"status": "green", "port": 8900, "latency_ms": 7},
    "steward": {"status": "green", "port": 8901, "latency_ms": 5}
  },
  "agents": {
    "oracle1": {"status": "active", "last_seen": "..."},
    "forgemaster": {"status": "active", "last_seen": "..."}
  },
  "total_services": 17,
  "healthy": 17
}
```

## Architecture

Shares the full service tree with [fleet-murmur](https://github.com/SuperInstance/fleet-murmur). This repo emphasizes health monitoring:

```
Beachcomb cycle (180s)
    ↓
Poll all service ports
    ↓
Check agent heartbeats
    ↓
Write health_report.json
    ↓
Auto-commit to git
```

## Beachcomb Scripts

- `scripts/beachcomb_v3.py` — Main beachcomb runner
- `scripts/oracle1-beachcomb.py` — Oracle1-specific beachcomb
- `scripts/purple_pincher.py` — PurplePincher monitoring

## Status Colors

| Color | Meaning |
|-------|---------|
| 🟢 green | Service responding normally |
| 🟡 yellow | Slow response or degraded |
| 🔴 red | Service down or unreachable |

## Related

- **fleet-murmur** — Full fleet service stack (same service tree)
- **quality-gate-stream** — Tile quality scoring (same service tree)
- **fleet-resonance** — Resonance detection between agents

## License

Apache-2.0
