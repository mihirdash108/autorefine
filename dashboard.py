"""
autorefine iteration dashboard — browser-based.
Serves a localhost dashboard with live charts showing refinement progress.

Usage:
    uv run dashboard.py              # open dashboard at http://localhost:8501
    uv run dashboard.py --port 9000  # custom port

Charts:
  1. Combined score trajectory
  2. Per-artifact scores
  3. Per-dimension pass/fail heatmap (binary) or scores (scale)
  4. Cumulative cost (USD)
  5. Token consumption per iteration
  6. Keep/Discard/Converge distribution
  7. Word count tracking
  8. Cross-document consistency
  9. Convergence monitor (consecutive discards)

Auto-refreshes every 5 seconds.
"""

import argparse
import json
import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT_DIR = Path(__file__).parent
HISTORY_PATH = ROOT_DIR / "eval_history.jsonl"
ACTIVITY_PATH = ROOT_DIR / "activity_log.jsonl"
STATE_PATH = ROOT_DIR / "eval_state.json"
RESULTS_PATH = ROOT_DIR / "results.tsv"


def load_history():
    entries = []
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return entries


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {}


def load_activity(limit=30):
    entries = []
    if ACTIVITY_PATH.exists():
        with open(ACTIVITY_PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return entries[-limit:]


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>autorefine dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script>if (typeof Chart === 'undefined') document.addEventListener('DOMContentLoaded', function() { document.getElementById('app').innerHTML = '<div style="text-align:center;padding:60px;color:#f85149"><h2>Chart.js failed to load</h2><p style="color:#7d8590;margin-top:12px">Check your internet connection, or view raw data at <a href="/api/data" style="color:#58a6ff">/api/data</a></p></div>'; });</script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; }
  h1 { font-size: 24px; margin-bottom: 4px; color: #f0f6fc; }
  .subtitle { color: #7d8590; font-size: 14px; margin-bottom: 24px; }
  .stats { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
  .stat { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 20px; min-width: 150px; }
  .stat-label { color: #7d8590; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-value { font-size: 28px; font-weight: 600; margin-top: 4px; }
  .stat-value.keep { color: #3fb950; }
  .stat-value.score { color: #58a6ff; }
  .stat-value.cost { color: #d2a8ff; }
  .stat-value.neutral { color: #e6edf3; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .chart-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
  .chart-card h3 { font-size: 14px; color: #7d8590; margin-bottom: 12px; font-weight: 500; }
  .chart-card canvas { width: 100% !important; }
  .wide { grid-column: 1 / -1; }
  .refresh { color: #7d8590; font-size: 12px; text-align: right; margin-top: 16px; }
  .status-banner { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 20px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
  .status-dot { width: 10px; height: 10px; border-radius: 50%; animation: pulse 2s infinite; }
  .status-dot.active { background: #3fb950; }
  .status-dot.stale { background: #d29922; }
  .status-dot.done { background: #7d8590; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .status-text { font-size: 14px; color: #e6edf3; }
  .status-age { color: #7d8590; font-size: 12px; margin-left: auto; }
  .activity-feed { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 24px; max-height: 250px; overflow-y: auto; }
  .activity-feed h3 { font-size: 14px; color: #7d8590; margin-bottom: 8px; }
  .activity-row { font-family: monospace; font-size: 12px; padding: 3px 0; display: flex; gap: 8px; }
  .activity-row .time { color: #7d8590; min-width: 65px; }
  .activity-row .event { padding: 1px 6px; border-radius: 3px; font-size: 11px; }
  .ev-iteration_start { background: #1f3d2a; color: #3fb950; }
  .ev-planning { background: #1a2744; color: #58a6ff; }
  .ev-editing { background: #3d2e00; color: #d29922; }
  .ev-edit_complete { background: #3d2e00; color: #d29922; }
  .ev-evaluating { background: #2d1a4e; color: #d2a8ff; }
  .ev-verdict { background: #1f3d2a; color: #3fb950; }
  .ev-error { background: #3d1a1a; color: #f85149; }
  .ev-setup { background: #1a2744; color: #58a6ff; }
  .activity-row .desc { color: #e6edf3; }
  .verdict-log { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 24px; max-height: 200px; overflow-y: auto; }
  .verdict-log h3 { font-size: 14px; color: #7d8590; margin-bottom: 8px; }
  .verdict-row { font-family: monospace; font-size: 13px; padding: 2px 0; }
  .v-keep { color: #3fb950; }
  .v-discard { color: #f85149; }
  .v-baseline { color: #58a6ff; }
  .v-converged { color: #d2a8ff; }
  .empty { text-align: center; padding: 60px; color: #7d8590; }
</style>
</head>
<body>
<h1>autorefine</h1>
<div class="subtitle">iteration dashboard &mdash; auto-refreshes every 5s</div>

<div id="app"></div>

<script>
const CHART_COLORS = {
  blue: '#58a6ff', green: '#3fb950', red: '#f85149', purple: '#d2a8ff',
  orange: '#d29922', cyan: '#39d2c0', pink: '#f778ba', gray: '#7d8590',
  yellow: '#e3b341',
};
const ARTIFACT_COLORS = [CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.purple, CHART_COLORS.orange, CHART_COLORS.cyan];

Chart.defaults.color = '#7d8590';
Chart.defaults.borderColor = '#21262d';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

let charts = {};

async function fetchData() {
  const resp = await fetch('/api/data');
  return resp.json();
}

function createChart(id, config) {
  if (charts[id]) charts[id].destroy();
  const ctx = document.getElementById(id);
  if (!ctx) return;
  charts[id] = new Chart(ctx, config);
}

function timeAgo(ts) {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  return Math.floor(s/3600) + 'h ago';
}

function renderActivity(activity) {
  if (!activity || activity.length === 0) return '';
  const last = activity[activity.length - 1];
  const age = (Date.now() - new Date(last.ts).getTime()) / 1000;
  const dotClass = age > 300 ? 'stale' : (last.event === 'verdict' && activity.length > 5 ? 'done' : 'active');
  const staleWarn = age > 300 ? ' — <span style="color:#d29922">no activity for ' + Math.floor(age/60) + 'm, agent may be stuck</span>' : '';
  const statusText = last.event === 'editing' ? 'Editing ' + (last.artifact || '') + ' / ' + (last.dimension || '')
    : last.event === 'evaluating' ? 'Running evaluation...'
    : last.event === 'verdict' ? 'Verdict: ' + (last.verdict || '')
    : last.event === 'planning' ? 'Planning: ' + (last.dimension || '')
    : last.event === 'iteration_start' ? 'Starting iteration ' + (last.iteration || '')
    : last.event || 'Working...';

  const banner = '<div class="status-banner"><div class="status-dot ' + dotClass + '"></div><div class="status-text">' + statusText + staleWarn + '</div><div class="status-age">' + timeAgo(last.ts) + '</div></div>';

  const feed = '<div class="activity-feed"><h3>Live Activity</h3>' +
    activity.slice().reverse().map(a => {
      const evCls = 'ev-' + (a.event || 'setup');
      const desc = a.description || a.dimension || a.strategy || a.verdict || a.artifact || '';
      return '<div class="activity-row"><span class="time">' + timeAgo(a.ts) + '</span><span class="event ' + evCls + '">' + (a.event || '?') + '</span><span class="desc">' + (a.iteration ? '#' + a.iteration + ' ' : '') + desc + '</span></div>';
    }).join('') + '</div>';

  return banner + feed;
}

function render(data) {
  const { history, state, activity } = data;
  const app = document.getElementById('app');

  // Show activity even before eval data exists
  const activityHtml = renderActivity(activity || []);

  if (!history || history.length === 0) {
    app.innerHTML = activityHtml + '<div class="empty"><p>No evaluation data yet.</p><p>Waiting for baseline to complete...</p></div>';
    return;
  }

  const latest = history[history.length - 1];
  const keeps = history.filter(h => h.verdict === 'KEEP').length;
  const discards = history.filter(h => h.verdict === 'DISCARD').length;
  const total = history.length - 1; // exclude baseline

  app.innerHTML = activityHtml + `
    <div class="stats">
      <div class="stat"><div class="stat-label">Iterations</div><div class="stat-value neutral">${latest.iteration}</div></div>
      <div class="stat"><div class="stat-label">Best Score</div><div class="stat-value score">${(state.best_combined_score || 0).toFixed(3)}</div></div>
      <div class="stat"><div class="stat-label">Keep Rate</div><div class="stat-value keep">${total > 0 ? Math.round(keeps/total*100) + '%' : 'N/A'}</div></div>
      <div class="stat"><div class="stat-label">Cost</div><div class="stat-value cost">$${(latest.cumulative_cost_usd || 0).toFixed(2)}</div></div>
      <div class="stat"><div class="stat-label">Latest Verdict</div><div class="stat-value ${latest.verdict === 'KEEP' ? 'keep' : latest.verdict === 'DISCARD' ? '' : 'score'}">${latest.verdict}</div></div>
      <div class="stat"><div class="stat-label">Consec. Discards</div><div class="stat-value neutral">${state.consecutive_discards || 0}</div></div>
    </div>

    <div class="grid">
      <div class="chart-card"><h3>Combined Score Trajectory</h3><canvas id="c-score"></canvas></div>
      <div class="chart-card"><h3>Per-Artifact Scores</h3><canvas id="c-artifacts"></canvas></div>
      <div class="chart-card"><h3>Token Consumption</h3><canvas id="c-tokens"></canvas></div>
      <div class="chart-card"><h3>Cumulative Cost (USD)</h3><canvas id="c-cost"></canvas></div>
      <div class="chart-card"><h3>Word Count Tracking</h3><canvas id="c-words"></canvas></div>
      <div class="chart-card"><h3>Cross-Document Consistency</h3><canvas id="c-crossdoc"></canvas></div>
      <div class="chart-card"><h3>Keep / Discard Distribution</h3><canvas id="c-verdicts"></canvas></div>
      <div class="chart-card"><h3>Consecutive Discards (Convergence)</h3><canvas id="c-convergence"></canvas></div>
      <div class="chart-card wide"><h3>Per-Dimension Scores</h3><canvas id="c-dimensions" height="100"></canvas></div>
    </div>

    <div class="verdict-log">
      <h3>Iteration Log</h3>
      ${history.slice().reverse().map(h => {
        const cls = h.verdict === 'KEEP' ? 'v-keep' : h.verdict === 'DISCARD' ? 'v-discard' : h.verdict === 'BASELINE' ? 'v-baseline' : 'v-converged';
        return '<div class="verdict-row"><span class="' + cls + '">#' + h.iteration + ' ' + h.verdict + '</span> score=' + (h.combined_score||0).toFixed(3) + ' cost=$' + (h.eval_cost_usd||0).toFixed(3) + ' tokens=' + (h.total_tokens||0) + '</div>';
      }).join('')}
    </div>

    <div class="refresh">Last updated: ${new Date().toLocaleTimeString()}</div>
  `;

  const labels = history.map(h => h.iteration);

  // 1. Combined score
  const verdictColors = history.map(h => h.verdict === 'KEEP' ? CHART_COLORS.green : h.verdict === 'DISCARD' ? CHART_COLORS.red : h.verdict === 'BASELINE' ? CHART_COLORS.blue : CHART_COLORS.purple);
  createChart('c-score', {
    type: 'line',
    data: { labels, datasets: [{
      label: 'Combined Score', data: history.map(h => h.combined_score),
      borderColor: CHART_COLORS.blue, backgroundColor: CHART_COLORS.blue + '20',
      fill: true, tension: 0.3, pointBackgroundColor: verdictColors, pointRadius: 5,
    }]},
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false } } }
  });

  // 2. Per-artifact scores
  const artifactNames = [...new Set(history.flatMap(h => Object.keys(h.artifact_scores || {})))];
  createChart('c-artifacts', {
    type: 'line',
    data: { labels, datasets: artifactNames.map((name, i) => ({
      label: name, data: history.map(h => (h.artifact_scores || {})[name] || null),
      borderColor: ARTIFACT_COLORS[i % ARTIFACT_COLORS.length], tension: 0.3, pointRadius: 3,
    }))},
    options: { scales: { y: { beginAtZero: false } } }
  });

  // 3. Token consumption
  createChart('c-tokens', {
    type: 'bar',
    data: { labels, datasets: [
      { label: 'Input', data: history.map(h => h.input_tokens || 0), backgroundColor: CHART_COLORS.blue + 'aa' },
      { label: 'Output', data: history.map(h => h.output_tokens || 0), backgroundColor: CHART_COLORS.purple + 'aa' },
    ]},
    options: { plugins: { legend: { position: 'top' } }, scales: { x: { stacked: true }, y: { stacked: true } } }
  });

  // 4. Cumulative cost
  createChart('c-cost', {
    type: 'line',
    data: { labels, datasets: [{
      label: 'Cumulative USD', data: history.map(h => h.cumulative_cost_usd),
      borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purple + '20',
      fill: true, tension: 0.3,
    }]},
    options: { plugins: { legend: { display: false } } }
  });

  // 5. Word counts
  const wcArtifacts = [...new Set(history.flatMap(h => Object.keys(h.word_counts || {})))];
  createChart('c-words', {
    type: 'line',
    data: { labels, datasets: wcArtifacts.map((name, i) => ({
      label: name, data: history.map(h => (h.word_counts || {})[name] || null),
      borderColor: ARTIFACT_COLORS[i % ARTIFACT_COLORS.length], tension: 0.3,
    }))},
    options: { scales: { y: { beginAtZero: false } } }
  });

  // 6. Cross-doc consistency
  createChart('c-crossdoc', {
    type: 'line',
    data: { labels, datasets: [{
      label: 'Cross-Doc', data: history.map(h => h.cross_doc),
      borderColor: CHART_COLORS.cyan, backgroundColor: CHART_COLORS.cyan + '20',
      fill: true, tension: 0.3,
    }]},
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false } } }
  });

  // 7. Verdict distribution
  const verdictCounts = { BASELINE: 0, KEEP: 0, DISCARD: 0, CONVERGED: 0 };
  history.forEach(h => { if (verdictCounts[h.verdict] !== undefined) verdictCounts[h.verdict]++; });
  createChart('c-verdicts', {
    type: 'doughnut',
    data: {
      labels: Object.keys(verdictCounts),
      datasets: [{ data: Object.values(verdictCounts), backgroundColor: [CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.red, CHART_COLORS.purple] }]
    },
    options: { plugins: { legend: { position: 'right' } } }
  });

  // 8. Consecutive discards
  let consecDiscards = [];
  let runCount = 0;
  history.forEach(h => {
    if (h.verdict === 'DISCARD') runCount++;
    else runCount = 0;
    consecDiscards.push(runCount);
  });
  createChart('c-convergence', {
    type: 'bar',
    data: { labels, datasets: [{
      label: 'Consecutive Discards', data: consecDiscards,
      backgroundColor: consecDiscards.map(v => v >= 5 ? CHART_COLORS.red : v >= 3 ? CHART_COLORS.orange : CHART_COLORS.gray + '60'),
    }]},
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: Math.max(6, ...consecDiscards) + 1 } } }
  });

  // 9. Per-dimension scores (latest iteration)
  const dimScores = latest.dimension_scores || {};
  const dimLabels = Object.keys(dimScores);
  const dimValues = Object.values(dimScores);
  const dimColors = dimValues.map(v => v >= 1 ? CHART_COLORS.green + 'cc' : CHART_COLORS.red + 'cc');
  if (dimLabels.length > 0) {
    createChart('c-dimensions', {
      type: 'bar',
      data: { labels: dimLabels.map(l => l.replace(/.*:/, '')), datasets: [{
        label: 'Score', data: dimValues, backgroundColor: dimColors,
      }]},
      options: {
        indexAxis: 'y', plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }
}

async function refresh() {
  try {
    const data = await fetchData();
    render(data);
  } catch (e) {
    console.error('Refresh failed:', e);
  }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

        elif parsed.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            data = {
                "history": load_history(),
                "state": load_state(),
                "activity": load_activity(),
            }
            self.wfile.write(json.dumps(data).encode())

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass  # Suppress request logging


def main():
    parser = argparse.ArgumentParser(description="autorefine iteration dashboard")
    parser.add_argument("--port", type=int, default=8501, help="Port to serve on")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    server = HTTPServer(("localhost", args.port), DashboardHandler)
    url = f"http://localhost:{args.port}"
    print(f"Dashboard running at {url}")
    print("Press Ctrl+C to stop.")

    if not args.no_open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
