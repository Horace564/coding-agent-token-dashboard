import { api, fmt } from '/web/app.js';
import { buildPromptTimeline, renderTurn } from '/web/routes/sessions.js';

const SORTS = [
  { key: 'tokens', label: 'Most tokens' },
  { key: 'recent', label: 'Most recent' },
];

function readSort() {
  const q = (location.hash.split('?')[1] || '');
  const m = /(?:^|&)sort=([^&]+)/.exec(q);
  const k = m && decodeURIComponent(m[1]);
  return SORTS.find(s => s.key === k) || SORTS[0];
}

function writeSort(key) {
  const base = (location.hash.replace(/^#/, '').split('?')[0]) || '/prompts';
  location.hash = '#' + base + '?sort=' + encodeURIComponent(key);
}

export default async function (root) {
  const sort = readSort();
  const rows = await api('/api/prompts?limit=100&sort=' + encodeURIComponent(sort.key));
  const sessionCache = new Map();
  const sessionContext = row => `${row.source === 'codex' ? 'Codex' : 'Claude'} · ${row.session_title || row.session_id.replace(/^codex:/, '').slice(0, 8)}`;
  const sortTabs = `
    <div class="range-tabs" role="tablist">
      ${SORTS.map(s => `<button data-sort="${s.key}" class="${s.key === sort.key ? 'active' : ''}">${s.label}</button>`).join('')}
    </div>`;
  const subtitle = sort.key === 'recent' ? 'Latest prompts' : 'Prompts with the most processed tokens';

  root.innerHTML = `
    <div class="flex" style="margin-bottom:14px">
      <h2 style="margin:0;font-size:16px;letter-spacing:-0.01em">Prompts</h2>
      <div class="spacer"></div>
      ${sortTabs}
    </div>
    <div class="card">
      <p class="muted" style="margin:0 0 14px">${subtitle}. Totals include every model call and cache read in a prompt. Expand a prompt to see its calls, tools, and token breakdown.</p>
      <div class="session-turn-list">
        ${rows.map((row, index) => renderTurn({
          prompt: { uuid: row.user_uuid, timestamp: row.timestamp, prompt_text: row.prompt_text },
          number: null,
          stats: {
            calls: row.model_calls, tools: row.tool_count,
            compact: row.compaction_count, tokens: row.total_tokens,
          },
          detailRows: [],
        }, new Map(), {
          label: 'prompt',
          time: fmt.ts(row.timestamp).slice(5),
          context: sessionContext(row),
          detailHtml: '<span class="muted">Loading details…</span>',
          index,
        })).join('') || '<p class="muted">No prompts yet.</p>'}
      </div>
    </div>`;

  root.querySelectorAll('.range-tabs button').forEach(btn => {
    btn.addEventListener('click', () => writeSort(btn.dataset.sort));
  });

  root.querySelectorAll('.session-turn[data-i]').forEach(details => {
    details.addEventListener('toggle', async () => {
      if (!details.open || details.dataset.loaded || details.dataset.loading) return;
      details.dataset.loading = '1';
      const row = rows[Number(details.dataset.i)];
      const body = details.querySelector('.session-turn-detail');
      try {
        if (!sessionCache.has(row.session_id)) {
          sessionCache.set(row.session_id, api('/api/sessions/' + encodeURIComponent(row.session_id)));
        }
        const timeline = buildPromptTimeline(await sessionCache.get(row.session_id));
        const entry = timeline.byPromptId.get(row.user_uuid);
        if (!entry) throw new Error('Prompt not found in session');
        if (!details.isConnected || !details.open) {
          delete details.dataset.loading;
          return;
        }
        const updated = document.createElement('div');
        updated.innerHTML = renderTurn(entry, timeline.callNumbers, {
          label: 'prompt',
          time: fmt.ts(row.timestamp).slice(5),
          context: sessionContext(row),
          sessionId: row.session_id,
          index: Number(details.dataset.i),
        });
        const replacement = updated.firstElementChild;
        replacement.open = true;
        replacement.dataset.loaded = '1';
        details.replaceWith(replacement);
      } catch (error) {
        sessionCache.delete(row.session_id);
        body.innerHTML = `<span class="muted">Could not load details: ${fmt.htmlSafe(String(error))}. Close and reopen to retry.</span>`;
        delete details.dataset.loading;
      }
    });
  });
}
