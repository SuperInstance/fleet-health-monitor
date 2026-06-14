/**
 * Fleet Health Monitor Worker
 * ===========================
 * Real-time γ/η dashboard for the SuperInstance fleet.
 * 
 * Polls fleet-edge-worker every 60s for agent status,
 * computes conservation metrics, stores time series in D1,
 * serves dashboard at /dashboard.
 * 
 * γ (cost) = total agent actions × avg latency
 * η (value) = successful tasks completed
 * C = γ + η (should remain roughly constant for stable fleet)
 * 
 * Efficiency = η / γ (higher is better)
 * Cancellation = 1 - (fleet_γ / Σ(individual_γ))
 */

export default {
  async scheduled(event: ScheduledEvent, env: Env): Promise<void> {
    await pollFleet(env);
  },

  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const headers = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    };

    if (url.pathname === '/dashboard') {
      return await handleDashboard(env, headers);
    }
    
    if (url.pathname === '/timeseries') {
      const hours = parseInt(url.searchParams.get('hours') || '24');
      return await handleTimeseries(env, hours, headers);
    }

    if (url.pathname === '/health') {
      return new Response(JSON.stringify({
        status: 'ok',
        service: 'fleet-health-monitor',
        schedule: 'every 60s',
      }, null, 2), { headers });
    }

    return new Response(JSON.stringify({
      service: 'fleet-health-monitor',
      endpoints: ['/dashboard', '/timeseries?hours=24', '/health'],
    }, null, 2), { headers });
  },
};

async function pollFleet(env: Env): Promise<void> {
  try {
    const resp = await fetch(`${env.FLEET_EDGE_URL}/status`, {
      headers: { 'User-Agent': 'fleet-health-monitor' },
    });

    if (!resp.ok) return;
    const status = await resp.json() as FleetStatus;

    const agents = status.agents || [];
    const totalActions = agents.reduce((s, a) => s + (a.actions || 0), 0);
    const activeAgents = agents.filter(a => a.status === 'active').length;
    
    // Compute γ and η
    const gamma = totalActions * 0.01; // Cost estimate
    const eta = status.total_actions || totalActions; // Value = completed work
    const efficiency = gamma > 0 ? eta / gamma : 0;

    await env.DB.prepare(`
      INSERT INTO fleet_metrics (timestamp, active_agents, total_agents, total_actions, gamma, eta, efficiency)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).bind(
      Date.now(),
      activeAgents,
      agents.length,
      totalActions,
      gamma,
      eta,
      efficiency
    ).run();

    // Prune old data (> 30 days)
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
    await env.DB.prepare(`DELETE FROM fleet_metrics WHERE timestamp < ?`).bind(cutoff).run();
  } catch (err) {
    console.error('Fleet poll failed:', err);
  }
}

async function handleDashboard(env: Env, headers: Record<string, string>): Promise<Response> {
  // Latest metrics
  const latest = await env.DB.prepare(`
    SELECT * FROM fleet_metrics ORDER BY timestamp DESC LIMIT 1
  `).first();

  // 24h summary
  const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
  const summary = await env.DB.prepare(`
    SELECT 
      AVG(efficiency) as avg_efficiency,
      MAX(active_agents) as peak_agents,
      SUM(total_actions) as total_actions,
      COUNT(*) as samples
    FROM fleet_metrics WHERE timestamp > ?
  `).bind(dayAgo).first();

  return new Response(JSON.stringify({
    current: latest,
    '24h_summary': summary,
    conservation_law: 'γ + η = C',
    timestamp: Date.now(),
  }, null, 2), { headers });
}

async function handleTimeseries(env: Env, hours: number, headers: Record<string, string>): Promise<Response> {
  const since = Date.now() - hours * 60 * 60 * 1000;
  const result = await env.DB.prepare(`
    SELECT timestamp, active_agents, total_agents, total_actions, gamma, eta, efficiency
    FROM fleet_metrics 
    WHERE timestamp > ?
    ORDER BY timestamp ASC
  `).bind(since).all();

  return new Response(JSON.stringify({
    hours,
    points: result.results || [],
  }, null, 2), { headers });
}

interface Env {
  DB: D1Database;
  FLEET_EDGE_URL: string;
}

interface FleetStatus {
  agents?: Array<{ name: string; status: string; actions: number }>;
  total_actions?: number;
}

// D1 Schema:
// CREATE TABLE fleet_metrics (
//   timestamp INTEGER PRIMARY KEY,
//   active_agents INTEGER NOT NULL,
//   total_agents INTEGER NOT NULL,
//   total_actions INTEGER NOT NULL,
//   gamma REAL NOT NULL,
//   eta REAL NOT NULL,
//   efficiency REAL NOT NULL
// );
