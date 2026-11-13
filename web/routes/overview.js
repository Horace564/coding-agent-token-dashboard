import { api, fmt } from '/web/app.js';
import { donutChart, groupedBarChart, stackedBarChart } from '/web/charts.js';

const RANGES = [
  { key: '7d',  label: '7d',  days: 7 },
  { key: '30d', label: '30d', days: 30 },
  { key: '90d', label: '90d', days: 90 },
  { key: 'all', label: 'All', days: null },
];

function readRange() {
  const q = (location.hash.split('?')[1] || '');
  const m = /(?:^|&)range=([^&]+)/.exec(q);
  const k = m && decodeURIComponent(m[1]);
  return RANGES.find(r => r.key === k) || RANGES[1];
}

function writeRange(key) {
  const base = (location.hash.replace(/^#/, '').split('?')[0]) || '/overview';
  location.hash = '#' + base + '?range=' + encodeURIComponent(key);
}

function sinceIso(range) {
  if (!range.days) return null;
  return new Date(Date.now() - range.days * 86400 * 1000).toISOString();
}

function withSince(url, since) {
  if (!since) return url;
  return url + (url.includes('?') ? '&' : '?') + 'since=' + encodeURIComponent(since);
}

export default async function (root) {
  const range = readRange();
  const since = sinceIso(range);

  const [totals, projects, sessions, tools, daily, byModel] = await Promise.all([
    api(withSince('/api/overview', since)),
    api(withSince('/api/projects', since)),
    api(withSince('/api/sessions?limit=10', since)),
    api(withSince('/api/tools', since)),
    api(withSince('/api/daily', since)),
    api(withSince('/api/by-model', since)),
  ]);

  const cacheCreate =
    (totals.cache_create_5m_tokens || 0) +
    (totals.cache_create_1h_tokens || 0) +
    (totals.cache_write_tokens || 0);

  const kpi = (label, compactVal, fullVal, cls = '') => `
    <div class="card kpi ${cls}">
      <div class="label">${label}</div>
      <div class="value" title="${fullVal}">${compactVal}</div>
    </div>`;

  const rangeTabs = `
    <div class="range-tabs" role="tablist">
      ${RANGES.map(r => `<button data-range="${r.key}" class="${r.key === range.key ? 'active' : ''}">${r.label}</button>`).join('')}
    </div>`;

  root.innerHTML = `
    <div class="flex" style="margin-bottom:14px">
      <h2 style="margin:0;font-size:16px;letter-spacing:-0.01em">Overview</h2>
      <span class="muted" style="font-size:12px">${range.days ? `last ${range.days} days` : 'all time'}</span>
      <div class="spacer"></div>
      ${rangeTabs}
    </div>

    <div class="row cols-6">
      ${kpi('Sessions',     fmt.int(totals.sessions),       fmt.int(totals.sessions))}
      ${kpi('Turns',        fmt.int(totals.turns),          fmt.int(totals.turns))}
      ${kpi('Fresh input',  fmt.compact(totals.input_tokens),       fmt.int(totals.input_tokens) + ' tokens')}
      ${kpi('Output',       fmt.compact(totals.output_tokens),      fmt.int(totals.output_tokens) + ' tokens')}
      ${kpi('Cache read',   fmt.compact(totals.cache_read_tokens),  fmt.int(totals.cache_read_tokens) + ' tokens')}
      ${kpi('Cache create', fmt.compact(cacheCreate),               fmt.int(cacheCreate) + ' tokens')}
    </div>

    <details class="card glossary" style="margin-top:16px">
      <summary><h3 style="display:inline-block;margin:0">What do these numbers mean?</h3><span class="muted" style="font-size:12px">— click to expand</span></summary>
      <dl>
        <dt>Session</dt><dd>One local Claude Code or Codex conversation.</dd>
        <dt>Turn</dt><dd>One user turn in a session. Codex turns are inferred from local usage records.</dd>
        <dt>Fresh input</dt><dd>Input tokens excluding cache reads and cache writes.</dd>
        <dt>Output tokens</dt><dd>Generated tokens, including reasoning tokens reported by Codex.</dd>
        <dt>Cache read</dt><dd>Input tokens reused from a prompt cache.</dd>
        <dt>Cache create</dt><dd>Input tokens written to cache. Claude and Codex report different cache details.</dd>
      </dl>
    </details>

    <div class="row cols-2" style="margin-top:16px">
      <div class="card">
        <h3>Your daily work</h3>
        <p class="muted" style="margin:-4px 0 10px;font-size:12px">Fresh input, output and cache writes across the selected source.</p>
        <div id="ch-daily-billable" style="height:260px"></div>
      </div>
      <div class="card">
        <h3>Daily cache reads</h3>
        <p class="muted" style="margin:-4px 0 10px;font-size:12px">Input tokens reused from cache.</p>
        <div id="ch-daily-cache" style="height:260px"></div>
      </div>
    </div>

    <div class="row cols-2" style="margin-top:16px">
      <div class="card"><h3>Tokens by project</h3><div id="ch-projects" style="height:320px"></div></div>
      <div class="card">
        <h3>Token usage by model</h3>
        <p class="muted" style="margin:-4px 0 4px;font-size:12px">Share of processed tokens per model and source.</p>
        <div id="ch-model" style="height:300px"></div>
      </div>
    </div>

    <div class="row cols-2" style="margin-top:16px">
      <div class="card">
        <h3>Tool use</h3>
        <p class="muted" style="margin:-4px 0 10px;font-size:12px">${fmt.int(tools.reduce((sum, tool) => sum + tool.calls, 0))} recorded calls in this range.</p>
        <p class="muted" style="margin:-4px 0 10px;font-size:12px">Codex exec calls are grouped by the nested tool visible in their input. Mixed and unknown calls remain separate; each exec counts once.</p>
        <div class="tool-use-table-wrap"><table>
          <thead><tr><th>tool</th><th>source</th><th class="num">calls</th><th class="num">sessions</th></tr></thead>
          <tbody>
            ${tools.map(tool => `<tr>
              <td class="blur-sensitive">${fmt.htmlSafe(tool.tool_name)}</td>
              <td><span class="badge">${fmt.htmlSafe(tool.source)}</span></td>
              <td class="num">${fmt.int(tool.calls)}</td>
              <td class="num">${fmt.int(tool.sessions)}</td>
            </tr>`).join('') || '<tr><td colspan="4" class="muted">No recorded tool calls in this range.</td></tr>'}
          </tbody>
        </table></div>
      </div>
      <div class="card">
        <h3 style="display:flex;align-items:center"><span>Recent sessions</span><span class="spacer"></span><a href="#/sessions" style="font-weight:400;font-size:12px">all →</a></h3>
        <table>
          <thead><tr><th>started</th><th>session</th><th class="num">tokens</th></tr></thead>
          <tbody>
            ${sessions.map(s => `
              <tr>
                <td class="mono">${fmt.ts(s.started)}</td>
                <td><a href="#/sessions/${encodeURIComponent(s.session_id)}">${fmt.htmlSafe(s.session_title || `Session ${s.session_id.replace(/^codex:/, '').slice(0, 8)}`)}</a> <span class="badge">${fmt.htmlSafe(s.source)}</span></td>
                <td class="num" title="${fmt.int(s.tokens)} tokens">${fmt.million(s.tokens)}</td>
              </tr>`).join('') || '<tr><td colspan="3" class="muted">no sessions in this range</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  `;

  // range buttons
  root.querySelectorAll('.range-tabs button').forEach(btn => {
    btn.addEventListener('click', () => writeRange(btn.dataset.range));
  });

  // Your daily work — billable tokens (input + output + cache create)
  stackedBarChart(document.getElementById('ch-daily-billable'), {
    categories: daily.map(d => d.day),
    series: [
      { name: 'input',        values: daily.map(d => d.input_tokens),        color: '#4A9EFF' },
      { name: 'output',       values: daily.map(d => d.output_tokens),       color: '#7C5CFF' },
      { name: 'cache create', values: daily.map(d => d.cache_create_tokens), color: '#E8A23B' },
    ],
  });

  // Daily cache reads (separate — scale is 100× larger)
  stackedBarChart(document.getElementById('ch-daily-cache'), {
    categories: daily.map(d => d.day),
    series: [
      { name: 'cache read', values: daily.map(d => d.cache_read_tokens), color: '#3FB68B' },
    ],
  });

  // by-model doughnut
  donutChart(document.getElementById('ch-model'),
    byModel.map(m => ({
      name: `${m.source}: ${fmt.modelShort(m.model) || 'unknown'}`,
      value: (m.input_tokens || 0) + (m.output_tokens || 0)
           + (m.cache_read_tokens || 0) + (m.cache_write_tokens || 0)
           + (m.cache_create_5m_tokens || 0) + (m.cache_create_1h_tokens || 0),
    })).filter(d => d.value > 0),
  );

  // tokens by project — input vs output
  const topProjects = projects.slice(0, 8);
  groupedBarChart(document.getElementById('ch-projects'), {
    categories: topProjects.map(p => {
      const name = p.project_name || p.project_slug;
      return name.length > 20 ? name.slice(0, 19) + '…' : name;
    }),
    series: [
      { name: 'input',  values: topProjects.map(p => p.input_tokens  || 0), color: '#4A9EFF' },
      { name: 'output', values: topProjects.map(p => p.output_tokens || 0), color: '#7C5CFF' },
    ],
  });

}
