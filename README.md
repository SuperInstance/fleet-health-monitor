# fleet-health-monitor

Fleet control plane for the Cocapn system. 18+ Python HTTP services that manage AI agent onboarding, training data pipelines, policy enforcement, and fleet coordination. Each service is a standalone HTTP server on a fixed port.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Fleet Runner :8899 — starts/stops all services             │
│                                                              │
│  Knowledge Layer                                            │
│  ├── PLATO :8847 — tile repository, provenance, trust       │
│  ├── Crab Trap :4042 — agent onboarding MUD                 │
│  └── MUD Telnet :7777 — telnet interface to MUD rooms       │
│                                                              │
│  Control Layer                                              │
│  ├── Conductor :4061 — state fusion, conflict resolution    │
│  ├── Gatekeeper :4053 — policy enforcement, readiness       │
│  ├── Archivist :4054 — history, searchable event store      │
│  ├── Pathfinder :4051 — routing graph between rooms         │
│  ├── Librarian :4052 — service catalog and room index       │
│  └── Orchestrator :8849 — task cascades                     │
│                                                              │
│  Agent Layer                                                │
│  ├── Keeper :8900 — fleet discovery, agent registry         │
│  ├── Agent API :8901 — agent registration API               │
│  ├── The Lock :4043 — iterative reasoning sessions          │
│  ├── Arena :4044 — self-play matches, ELO leaderboard       │
│  └── Grammar :4045 — recursive rule evolution               │
│                                                              │
│  Monitoring Layer                                           │
│  ├── PP Monitor :8851 — live dashboard                      │
│  ├── Tile Scorer :8852 — tile quality scoring               │
│  ├── Dashboard :4046 — web dashboard                        │
│  └── Rate Attention :4056 — rate limiting                   │
│                                                              │
│  Other Services                                             │
│  ├── Shell :8848 — command shell                            │
│  ├── Adaptive MUD :8850 — adaptive difficulty               │
│  ├── Domain Rooms :4050 — domain-specific rooms             │
│  ├── Nexus :4047 — federated knowledge                      │
│  └── Web Terminal :4060 — browser terminal                  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Start all 18 services
bash scripts/start-fleet.sh

# Check health
bash scripts/start-fleet.sh --check

# Stop all
bash scripts/start-fleet.sh --stop
```

Requires Python 3.10+, 4GB RAM, API keys in `~/.bashrc` (`DEEPSEEK_API_KEY`, `GROQ_API_KEY`, or `DEEPINFRA_KEY`).

## Service Details

### Fleet Runner — :8899

Control plane that starts, stops, and monitors all services. Each service runs as a subprocess.

```bash
# Start a single service
curl -X POST localhost:8899/start -d '{"service": "plato"}'

# Restart
curl -X POST localhost:8899/restart -d '{"service": "crab-trap"}'

# Stop everything
curl -X POST localhost:8899/stop -d '{"service": "all"}'

# Status of all 18 services
curl localhost:8899/status
```

### Conductor — :4061

Central brain that fuses state from every service into a unified execution plan. Detects conflicts (down dependencies, stuck agents, empty rooms) and auto-resolves them via directives.

```bash
# Trigger full fleet state fusion
curl localhost:4061/fuse

# Get unified summary
curl localhost:4061/summary
# → {"services": "17/18 up", "agents": "5 registered, 3 active", "conflicts": 1, ...}

# List detected conflicts
curl localhost:4061/conflicts

# Auto-resolve conflicts
curl localhost:4061/resolve

# Create a directive
curl -X POST localhost:4061/directive \
  -d '{"action": "restart_service", "target": "plato", "priority": "high"}'

# Fleet timeline
curl localhost:4061/timeline?limit=30
```

Conflict types the Conductor detects:
- `dependency_down` — service X depends on service Y which is down
- `agent_stuck` — agent at high stage but low readiness score
- `empty_room` — knowledge room with zero tiles

### Gatekeeper — :4053

Policy enforcement and readiness validation. 7 default policies:

| ID | Policy | Check |
|----|--------|-------|
| P001 | agent_must_exist | Agent registered |
| P002 | room_not_restricted | Room accessible for agent role |
| P003 | stage_sufficient | Agent stage ≥ room/job minimum |
| P004 | submission_integrity | Required fields present |
| P005 | service_dependency_ready | Required services healthy |
| P006 | rate_limit | Agent within rate limits |
| P007 | reputation_floor | Reputation above threshold |

```bash
# Check agent readiness
curl "localhost:4053/readiness?agent=oracle1"

# List policies
curl localhost:4053/policies

# Get agent registry
curl localhost:4053/agents
```

### PLATO — :8847

Central tile repository. All agent knowledge flows through here. Zero-trust validation, provenance signing, explainability tracking.

```bash
curl localhost:8847/status        # tile counts, room stats
curl localhost:8847/rooms         # list rooms with tile counts
curl localhost:8847/room/arithmetic  # tiles for a room
curl localhost:8847/provenance/trust  # agent trust scores
```

### Keeper — :8900

Fleet discovery using beacon protocol. Agents register capabilities, Keeper matches them to tasks. Uses `keeper_beacon` (AgentRegistry, CapabilityMatcher, ProximityScorer) and `bottle_protocol` (TidePool, BottleRouter) for inter-agent messaging.

### Archivist — :4054

Searchable event history. Stores every submission, decision, and state change as JSONL. Queryable by agent, service, room, outcome, time range.

```bash
curl "localhost:4054/trends?hours=24"
curl "localhost:4054/query?agent=oracle1&limit=20"
```

### PP Monitor — :8851

Live dashboard that aggregates metrics from PLATO, Crab Trap, Shell, and Adaptive MUD. Tracks tile rate, active agents, top domains.

## Necrosis Detection

The Conductor performs necrosis detection during state fusion (`GET /fuse`):

1. Polls each service's health endpoint
2. Services that don't respond get `status: "down"`
3. Downstream dependencies of dead services generate `dependency_down` conflicts
4. Auto-resolution creates `restart_service` directives

The Fleet Runner (`:8899`) can also detect dead processes:
- Child process exits → `poll()` returns non-None
- Port not listening → `ss -tlnp` check
- Manual restart via `POST /restart`

## Health Check Configuration

```bash
# Quick check all ports
bash scripts/start-fleet.sh --check

# Per-service health
for port in 8847 4042 4061 4053 4054 8899 8900; do
  echo -n ":$port → "
  curl -s "http://localhost:$port/" | python3 -c "import sys,json; print(json.load(sys.stdin).get('service','ok'))" 2>/dev/null || echo "DOWN"
done
```

Each service exposes a `GET /` endpoint returning its name and status. Services that depend on others check upstream health on each request.

## Data Directories

| Path | Service | Contents |
|------|---------|----------|
| `data/plato-server-data/` | PLATO | tiles, hashes, rooms |
| `data/keeper/` | Keeper | fleet.json (agent registry) |
| `data/conductor/` | Conductor | directives.jsonl, events.jsonl |
| `data/gatekeeper/` | Gatekeeper | audit.jsonl |
| `data/archivist/` | Archivist | archive.jsonl, snapshots/ |
| `data/crab-trap/` | Crab Trap | harvested-tiles.jsonl, task-queue.json |

All data is JSONL (append-only) or JSON files. No database required.

## Project Structure

```
fleet/
├── __init__.py
├── agent/              # Agent context and identity
│   ├── context.py
│   └── __init__.py
├── equipment/          # Shared clients
│   ├── matrix.py       # Matrix/Conduwuit client
│   ├── models.py       # FleetModelClient (LLM API)
│   ├── mud.py          # MUD utilities
│   └── plato.py        # PlatoClient
├── services/           # All 30+ services
│   ├── conductor.py    # :4061 — control plane
│   ├── gatekeeper.py   # :4053 — policy engine
│   ├── archivist.py    # :4054 — history store
│   ├── keeper.py       # :8900 — fleet discovery
│   ├── fleet_runner.py # :8899 — service launcher
│   ├── plato.py        # :8847 — tile repository
│   ├── crab_trap.py    # :4042 — agent MUD
│   └── ...             # 20+ more services
├── skills/
└── vessel/
scripts/
├── start-fleet.sh      # Start/check/stop all services
├── keeper.py           # Keeper launcher
├── agent-api.py        # Agent API launcher
└── ...                 # Service launchers
```

## Related Repos

| Repo | Purpose |
|------|--------|
| [`plato-types`](https://github.com/SuperInstance/plato-types) | Core types for the PLATO tile protocol |
| [`agent-field`](https://github.com/SuperInstance/agent-field) | Shared tensor field for agent room coordination |
| [`constraint-inference`](https://github.com/SuperInstance/constraint-inference) | Reverse-engineers constraints from user behavior |
| [`captains-log`](https://github.com/SuperInstance/captains-log) | Oracle1 personal-agentic-growth diary |

## License

MIT
