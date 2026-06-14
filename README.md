# Fleet Health Monitor

> Real-time γ/η dashboard for the SuperInstance fleet

## What It Does

Polls `fleet-edge-worker` every 60 seconds for agent status. Computes conservation metrics (γ cost, η value, efficiency). Stores time series in D1. Serves dashboard + timeseries endpoints.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Current + 24h summary metrics |
| GET | `/timeseries?hours=24` | Time series data |
| GET | `/health` | Health check |

## Conservation Mapping

- **γ (cost)**: total agent actions × avg latency
- **η (value)**: successful tasks completed
- **Efficiency**: η / γ
- **Cancellation**: 1 - (fleet_γ / Σ(individual_γ))

## Deployment

```bash
wrangler d1 create fleet-health
wrangler deploy
```

## Schedule

Every 60 seconds via cron trigger.
