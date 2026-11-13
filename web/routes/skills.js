import { api, fmt, state } from '/web/app.js';
import { barChart } from '/web/charts.js';

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
  const base = (location.hash.replace(/^#/, '').split('?')[0]) || '/skills';
  location.hash = '#' + base + '?range=' + encodeURIComponent(key);
}

function sinceIso(range) {
  if (!range.days) return null;
  return new Date(Date.now() - range.days * 86400 * 1000).toISOString();
}

export default async function (root) {
  const range = readRange();
  const since = sinceIso(range);
  const url = '/api/skills' + (since ? '?since=' + encodeURIComponent(since) : '');
  const skills = await api(url);

  const totalInvocations = skills.reduce((s, r) => s + r.invocations, 0);
  const uniqueSkills = new Set(skills.map(r => r.skill)).size;
  const sourceNote = state.source === 'codex' ? 'Codex uses inferred from SKILL.md reads'
    : state.source === 'claude' ? 'Claude Code Skill tool calls'
    : 'Claude Code Skill calls and inferred Codex SKILL.md reads';

  const rangeTabs = `
    <div class="range-tabs" role="tablist">
      ${RANGES.map(r => `<button data-range="${r.key}" class="${r.key === range.key ? 'active' : ''}">${r.label}</button>`).join('')}
    </div>`;

  root.innerHTML = `
    <div class="flex" style="margin-bottom:14px">
      <h2 style="margin:0;font-size:16px;letter-spacing:-0.01em">Skills</h2>
      <span class="muted" style="font-size:12px">${sourceNote}</span>
      <span class="muted" style="font-size:12px">${range.days ? `last ${range.days} days` : 'all time'}</span>
      <div class="spacer"></div>
      ${rangeTabs}
    </div>

    <div class="row cols-2">
      <div class="card kpi"><div class="label">Unique skills used</div><div class="value">${fmt.int(uniqueSkills)}</div></div>
      <div class="card kpi"><div class="label">Observed uses</div><div class="value">${fmt.int(totalInvocations)}</div></div>
    </div>

    <div class="card" style="margin-top:16px">
      <h3>Top skills (by uses)</h3>
      <div id="ch-skills" style="height:320px"></div>
    </div>

    <div class="card" style="margin-top:16px">
      <h3>All skills</h3>
      <p class="muted" style="margin:-4px 0 14px;font-size:12px">"Tokens per call" estimates the size of a local <code>SKILL.md</code> file; it is not measured token usage. Codex counts one read per skill per turn.</p>
      <table>
        <thead><tr>
          <th>skill</th>
          <th>source</th>
          <th class="num">uses</th>
          <th class="num">tokens per call</th>
          <th class="num">sessions</th>
          <th>last used</th>
        </tr></thead>
        <tbody>
          ${skills.map(s => `
            <tr>
              <td><span class="badge">${fmt.htmlSafe(s.skill)}</span></td>
              <td>${s.source === 'codex' ? 'Codex (inferred)' : 'Claude Code'}</td>
              <td class="num">${fmt.int(s.invocations)}</td>
              <td class="num">${s.tokens_per_call == null ? '<span class="muted">—</span>' : fmt.int(s.tokens_per_call)}</td>
              <td class="num">${fmt.int(s.sessions)}</td>
              <td class="mono">${fmt.ts(s.last_used)}</td>
            </tr>`).join('') || '<tr><td colspan="6" class="muted">no skills invoked in this range</td></tr>'}
        </tbody>
      </table>
    </div>
  `;

  root.querySelectorAll('.range-tabs button').forEach(btn => {
    btn.addEventListener('click', () => writeRange(btn.dataset.range));
  });

  const top = skills.slice(0, 12);
  barChart(document.getElementById('ch-skills'), {
    categories: top.map(t => {
      const label = state.source === 'all' ? `${t.skill} (${t.source})` : t.skill;
      return label.length > 26 ? label.slice(0, 25) + '…' : label;
    }),
    values: top.map(t => t.invocations),
    color: '#3FB68B',
  });
}
