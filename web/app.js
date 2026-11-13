// app.js — router, state, fetch helpers

export const $  = (sel, root=document) => root.querySelector(sel);
export const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

const COMPACT = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
const MILLIONS = new Intl.NumberFormat('en', { maximumSignificantDigits: 3 });
export const fmt = {
  int:   n => (n ?? 0).toLocaleString(),
  compact: n => COMPACT.format(n ?? 0),
  million: n => `${MILLIONS.format((n || 0) / 1_000_000)}M`,
  pct:   n => n == null ? '—' : (n * 100).toFixed(0) + '%',
  short: (s, n=80) => s == null ? '' : (s.length > n ? s.slice(0, n - 1) + '…' : s),
  htmlSafe: s => (s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  modelClass: m => {
    const s = (m || '').toLowerCase();
    if (s.includes('opus'))   return 'opus';
    if (s.includes('sonnet')) return 'sonnet';
    if (s.includes('haiku'))  return 'haiku';
    return '';
  },
  modelShort: m => (m || '').replace('claude-', ''),
  ts: t => (t || '').slice(0, 16).replace('T', ' '),
};

export async function api(path, opts) {
  const url = !opts && path.startsWith('/api/') && state.source !== 'all'
    ? path + (path.includes('?') ? '&' : '?') + 'source=' + encodeURIComponent(state.source)
    : path;
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

export const state = { source: localStorage.getItem('td.source') || 'all' };

const ROUTES = {
  '/overview': () => import('/web/routes/overview.js'),
  '/prompts':  () => import('/web/routes/prompts.js'),
  '/sessions': () => import('/web/routes/sessions.js'),
  '/skills':   () => import('/web/routes/skills.js'),
};

function buildTopbar() {
  const wrap = document.createElement('header');
  wrap.className = 'topbar';
  wrap.innerHTML = `
    <div class="brand">Token Dashboard</div>
    <nav>
      ${Object.keys(ROUTES).map(p => `<a href="#${p}" data-route="${p}">${p.slice(1)}</a>`).join('')}
    </nav>
    <div class="spacer"></div>
    <select id="source-filter" aria-label="Usage source">
      <option value="all">All sources</option>
      <option value="claude">Claude Code</option>
      <option value="codex">Codex</option>
    </select>
    <span class="pill muted" title="Cmd/Ctrl+B blurs sensitive text">⌘B blur</span>
  `;
  document.body.prepend(wrap);
}

function setActiveTab(routeKey) {
  $$('header.topbar nav a').forEach(a => a.classList.toggle('active', a.dataset.route === routeKey));
}

async function render() {
  const hash = location.hash.replace(/^#/, '') || '/overview';
  const path = hash.split('?')[0];
  let key = path;
  if (path.startsWith('/sessions/')) key = '/sessions';
  if (!ROUTES[key]) key = '/overview';
  setActiveTab(key);
  const loader = ROUTES[key];
  const mod = await loader();
  $('#app').innerHTML = '';
  try {
    await mod.default($('#app'));
  } catch (e) {
    $('#app').innerHTML = `<div class="card"><h2>Error</h2><pre>${fmt.htmlSafe(String(e.stack || e))}</pre></div>`;
  }
}

async function boot() {
  buildTopbar();
  if (!['all', 'claude', 'codex'].includes(state.source)) state.source = 'all';
  $('#source-filter').value = state.source;
  $('#source-filter').addEventListener('change', e => {
    state.source = e.target.value;
    localStorage.setItem('td.source', state.source);
    render();
  });
  window.addEventListener('hashchange', render);
  await render();

  // Privacy blur (Cmd+B / Ctrl+B)
  window.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      document.body.classList.toggle('privacy-on');
    }
  });

  // SSE diff stream
  try {
    const es = new EventSource('/api/stream');
    let serverInstance = null;
    es.onmessage = ev => {
      try {
        const evt = JSON.parse(ev.data);
        if (evt.type === 'server') {
          if (serverInstance !== null && serverInstance !== evt.instance) {
            location.reload();
            return;
          }
          serverInstance = evt.instance;
        }
        if (evt.type === 'scan') render();
      } catch {}
    };
  } catch {}
}

boot();
