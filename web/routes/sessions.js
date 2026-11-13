import { api, fmt } from '/web/app.js';
import { promptPreview } from '/web/prompt-preview.js';

const safe = value => fmt.htmlSafe(String(value ?? ''));
const shortSessionId = id => (id || '').replace(/^codex:/, '').slice(0, 8);
export const millionTokens = fmt.million;
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
  const base = (location.hash.replace(/^#/, '').split('?')[0]) || '/sessions';
  location.hash = '#' + base + '?sort=' + encodeURIComponent(key);
}

export function eventsFor(row) {
  try {
    const events = JSON.parse(row.activity_json || '[]');
    if (Array.isArray(events) && events.length) return events;
  } catch (_) { /* Old imports have no activity data. */ }
  try {
    const tools = JSON.parse(row.tool_calls_json || '[]');
    return Array.isArray(tools) ? tools.map(tool => ({ kind: 'tool', ...tool })) : [];
  } catch (_) { return []; }
}

export function totalTokens(row) {
  return (row.input_tokens || 0) + (row.output_tokens || 0)
    + (row.cache_read_tokens || 0) + (row.cache_write_tokens || 0)
    + (row.cache_create_5m_tokens || 0) + (row.cache_create_1h_tokens || 0);
}

function toolLabel(tool) {
  const name = tool.name || 'tool';
  const input = String(tool.input || '');
  const nested = [...new Set([...input.matchAll(/\btools\.([A-Za-z_]\w*)\s*\(/g)].map(m => m[1]))];
  const command = input.match(/(?:\bcmd|["']cmd["'])\s*:\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/);
  let detail = tool.target || '';
  if (command) {
    if (command[1].startsWith('"')) {
      try { detail = JSON.parse(command[1]); } catch (_) { /* Keep the tool name. */ }
    } else {
      detail = command[1].slice(1, -1);
    }
  }
  if (!detail && nested.length) detail = nested.join(', ');
  if (!detail && input) detail = input.replace(/\s+/g, ' ').trim();
  return `${name}${detail ? ` · ${fmt.short(detail, 110)}` : ''}`;
}

function renderEvent(event) {
  const when = event.timestamp ? `<span class="mono muted">${safe(event.timestamp.slice(11, 19))}</span>` : '';
  if (event.kind === 'compaction') {
    const window = event.window_number ? ` · window ${safe(event.window_number)}` : '';
    return `<div class="session-event compaction-event"><span class="badge">compact</span> ${when}${window}</div>`;
  }
  if (event.kind === 'tool') {
    const output = event.output == null ? '<span class="muted">Result pending or unavailable</span>'
      : `<pre class="blur-sensitive">${safe(event.output)}</pre>${event.output_truncated ? '<span class="muted">Result preview truncated</span>' : ''}`;
    const duration = event.timestamp && event.completed_at
      ? Math.max(0, (Date.parse(event.completed_at) - Date.parse(event.timestamp)) / 1000)
      : null;
    const durationLabel = Number.isFinite(duration) ? ` · ${duration.toFixed(1)}s` : '';
    return `<div class="session-event">
      <div><span class="badge">tool</span> ${when} <span class="blur-sensitive">${safe(toolLabel(event))}</span><span class="muted">${durationLabel}</span></div>
      <details class="session-event-detail"><summary>Arguments and result</summary>
        <div class="muted">${safe(event.call_id || '')}</div>
        <div class="muted">Arguments${event.input_truncated ? ' · preview truncated' : ''}</div>
        <pre class="blur-sensitive">${safe(event.input || '')}</pre>
        <div class="muted">Result</div>${output}
      </details>
    </div>`;
  }
  if (event.kind === 'message' || event.kind === 'reasoning_summary' || event.kind === 'tool_output') {
    const label = event.kind === 'message' ? (event.phase || 'message')
      : event.kind === 'reasoning_summary' ? 'reasoning summary' : 'tool result';
    const content = event.text || event.output || '';
    return `<div class="session-event"><span class="badge">${safe(label)}</span> ${when}
      <pre class="blur-sensitive">${safe(content)}</pre>
      ${event.truncated || event.output_truncated ? '<span class="muted">Preview truncated</span>' : ''}
    </div>`;
  }
  return '';
}

function renderActivity(row) {
  const events = eventsFor(row);
  if (!events.length) return '<span class="muted">No recorded actions</span>';
  const tools = events.filter(event => event.kind === 'tool');
  const messages = events.filter(event => event.kind === 'message');
  const compaction = events.some(event => event.kind === 'compaction');
  const labels = [
    ...messages.map(event => fmt.short((event.text || '').replace(/\s+/g, ' '), 90)),
    ...tools.slice(0, 2).map(toolLabel),
    tools.length > 2 ? `+${tools.length - 2} tools` : '',
    compaction ? 'Context compacted' : '',
  ].filter(Boolean);
  const label = labels.length ? fmt.short(labels.join(' · '), 180) : 'Recorded activity';
  return `<details class="call-activity"><summary class="blur-sensitive">${safe(label)}</summary>
    <div class="call-activity-body">
      ${events.map(renderEvent).join('')}
      <div class="session-call-meta muted">response ${safe(row.message_id || 'unknown')}
        · ${fmt.int(row.reasoning_output_tokens || 0)} reasoning tokens
        ${row.cache_write_tokens ? ` · ${fmt.int(row.cache_write_tokens)} cache write` : ''}
      </div>
    </div>
  </details>`;
}

function renderPrompt(prompt) {
  if (!prompt) return '<span class="muted">Prompt unavailable</span>';
  if (prompt.length <= 140) return `<span class="blur-sensitive">${safe(prompt)}</span>`;
  return `<details class="call-activity"><summary class="blur-sensitive">${safe(fmt.short(prompt.replace(/\s+/g, ' '), 140))}</summary>
    <pre class="session-prompt-full blur-sensitive">${safe(prompt)}</pre></details>`;
}

export function buildPromptTimeline(turns) {
  const source = turns[0]?.source || 'claude';
  const isPromptTurn = t => t.type === 'user' && (source === 'codex' || !!t.prompt_text);
  const byId = new Map(turns.map(t => [t.uuid, t]));
  const entries = [];
  const byPromptId = new Map();
  const callNumbers = new Map();
  let turnNumber = 0;
  for (const t of turns) {
    if (!isPromptTurn(t)) continue;
    const entry = {
      prompt: t, number: ++turnNumber,
      stats: { calls: 0, tools: 0, compact: 0, tokens: 0 }, detailRows: [],
    };
    entries.push(entry);
    byPromptId.set(t.uuid, entry);
  }
  let lastPromptId = null;
  const fallbackTurn = new Map();
  for (const t of turns) {
    if (isPromptTurn(t)) lastPromptId = t.uuid;
    fallbackTurn.set(t.uuid, lastPromptId);
  }
  function parentTurnId(row) {
    const seen = new Set();
    let parent = row.parent_uuid;
    while (parent && !seen.has(parent)) {
      if (byPromptId.has(parent)) return parent;
      seen.add(parent);
      parent = byId.get(parent)?.parent_uuid;
    }
    return fallbackTurn.get(row.uuid);
  }
  const unassigned = {
    prompt: null, number: null,
    stats: { calls: 0, tools: 0, compact: 0, tokens: 0 }, detailRows: [],
  };
  for (const t of turns) {
    if (isPromptTurn(t)) continue;
    const entry = byPromptId.get(parentTurnId(t)) || unassigned;
    entry.detailRows.push(t);
    if (t.type !== 'assistant') continue;
    entry.stats.calls++;
    entry.stats.tokens += totalTokens(t);
    entry.stats.tools += eventsFor(t).filter(e => e.kind === 'tool').length;
    entry.stats.compact += eventsFor(t).filter(e => e.kind === 'compaction').length;
    callNumbers.set(t.uuid, entry.stats.calls);
  }
  return { entries, byPromptId, callNumbers, unassigned, promptCount: turnNumber };
}

function renderDetailRow(t, callNumbers) {
  if (t.type === 'user') {
    return `<tr class="session-result-row">
      <td class="mono">${safe((t.timestamp || '').slice(11, 19))}</td>
      <td><span class="badge">tool result</span></td>
      <td></td>
      <td class="muted">${renderPrompt(t.prompt_text)}</td>
      <td colspan="4"></td>
    </tr>`;
  }
  const compaction = eventsFor(t).some(e => e.kind === 'compaction');
  return `<tr class="session-call-row${compaction ? ' session-compact-row' : ''}">
    <td class="mono">${safe((t.timestamp || '').slice(11, 19))}</td>
    <td>call ${fmt.int(callNumbers.get(t.uuid) || 0)}${compaction ? ' <span class="badge">compact</span>' : ''}${t.is_sidechain ? ' <span class="badge">side</span>' : ''}</td>
    <td>${t.model ? `<span class="badge ${fmt.modelClass(t.model)}">${safe(fmt.modelShort(t.model))}</span>` : ''}${t.reasoning_effort ? `<div class="muted">${safe(t.reasoning_effort)}</div>` : ''}</td>
    <td>${renderActivity(t)}</td>
    <td class="num">${fmt.int(t.input_tokens)}</td>
    <td class="num">${fmt.int(t.output_tokens)}</td>
    <td class="num">${fmt.int(t.cache_read_tokens)}</td>
    <td class="num">${fmt.int(totalTokens(t))}</td>
  </tr>`;
}

export function renderTurnDetail(entry, callNumbers, sessionId = null) {
  const { prompt, detailRows } = entry;
  return `${prompt ? `<div class="muted">Full prompt</div><pre class="session-prompt-full blur-sensitive">${safe(prompt.prompt_text || '')}</pre>` : ''}
    ${detailRows.length ? `<div class="session-table-wrap"><table class="session-detail-table">
      <thead><tr><th>time</th><th>step</th><th>model</th><th class="blur-sensitive">tools / result</th><th class="num">fresh in</th><th class="num">out</th><th class="num">cache rd</th><th class="num">total</th></tr></thead>
      <tbody>${detailRows.map(t => renderDetailRow(t, callNumbers)).join('')}</tbody>
    </table></div>` : '<p class="muted">No recorded model calls.</p>'}
    ${sessionId ? `<div class="session-prompt-link"><a href="#/sessions/${encodeURIComponent(sessionId)}">Open session →</a></div>` : ''}`;
}

export function renderTurn(entry, callNumbers, options = {}) {
  const { prompt, number, stats, detailRows } = entry;
  const label = options.label || (prompt ? `turn ${fmt.int(number)}` : 'other');
  const time = options.time || (prompt?.timestamp || detailRows[0]?.timestamp || '').slice(11, 19);
  const text = prompt ? (prompt.prompt_text || 'Prompt unavailable') : 'Activity without a recorded prompt';
  const preview = promptPreview(text, 100);
  const context = options.context
    ? `<small class="session-turn-context blur-sensitive">${safe(options.context)}</small>` : '';
  const dataIndex = Number.isInteger(options.index) ? ` data-i="${options.index}"` : '';
  return `<details class="session-turn"${dataIndex}>
    <summary>
      <span class="session-turn-index mono">
        <span>${safe(label)}</span>
        <span class="muted">${safe(time)}</span>
        ${stats.compact ? `<span class="session-turn-compact" title="${fmt.int(stats.compact)} context compactions">compact ×${fmt.int(stats.compact)}</span>` : ''}
      </span>
      <span class="session-turn-preview${context ? ' has-context' : ''}"><span class="session-turn-preview-text blur-sensitive">${safe(preview)}</span>${context}</span>
      <span class="session-turn-stat session-turn-calls"><strong>${fmt.int(stats.calls)}</strong><small>calls</small></span>
      <span class="session-turn-stat session-turn-tools"><strong>${fmt.int(stats.tools)}</strong><small>tools</small></span>
      <span class="session-turn-stat session-turn-tokens" title="${fmt.int(stats.tokens)} tokens"><strong>${millionTokens(stats.tokens)}</strong><small>tokens</small></span>
    </summary>
    <div class="session-turn-detail">${options.detailHtml ?? renderTurnDetail(entry, callNumbers, options.sessionId)}</div>
  </details>`;
}

export default async function (root) {
  const id = decodeURIComponent(location.hash.split('/')[2] || '');
  if (!id) return renderList(root);
  return renderSession(root, id);
}

async function renderList(root) {
  const sort = readSort();
  const list = await api('/api/sessions?limit=100&sort=' + encodeURIComponent(sort.key));
  const missingCompactionCounts = list.some(s => s.compaction_count == null);
  const sortTabs = `
    <div class="range-tabs" role="tablist">
      ${SORTS.map(s => `<button data-sort="${s.key}" class="${s.key === sort.key ? 'active' : ''}">${s.label}</button>`).join('')}
    </div>`;
  root.innerHTML = `
    <div class="flex" style="margin-bottom:14px">
      <h2 style="margin:0;font-size:16px;letter-spacing:-0.01em">Sessions</h2>
      <div class="spacer"></div>
      ${sortTabs}
    </div>
    <div class="card">
      ${missingCompactionCounts ? '<p class="muted" style="margin:0 0 12px">Compaction counts are unavailable from the running server. Restart the dashboard to load them.</p>' : ''}
      <div class="session-table-wrap"><table>
        <thead><tr><th>started</th><th>session</th><th>project</th><th>source</th><th class="num">compacts</th><th class="num">turns</th><th class="num">tokens</th></tr></thead>
        <tbody>
          ${list.map(s => `
            <tr>
              <td class="mono">${fmt.ts(s.started)}</td>
              <td><a href="#/sessions/${encodeURIComponent(s.session_id)}">${safe(s.session_title || `Session ${shortSessionId(s.session_id)}`)}</a></td>
              <td title="${safe(s.project_slug)}">${safe(s.project_name || s.project_slug)}</td>
              <td><span class="badge">${safe(s.source)}</span></td>
              <td class="num">${s.compaction_count == null ? '<span class="muted">—</span>' : `<span class="session-compact-count${s.compaction_count ? ' is-active' : ''}" title="${fmt.int(s.compaction_count)} context compactions">${fmt.int(s.compaction_count)}</span>`}</td>
              <td class="num">${fmt.int(s.turns)}</td>
              <td class="num" title="${fmt.int(s.tokens)} tokens">${millionTokens(s.tokens)}</td>
            </tr>`).join('')}
        </tbody>
      </table></div>
    </div>`;
  root.querySelectorAll('.range-tabs button').forEach(btn => {
    btn.addEventListener('click', () => writeSort(btn.dataset.sort));
  });
}

async function renderSession(root, id) {
  const turns = await api('/api/sessions/' + encodeURIComponent(id));
  if (!turns.length) {
    root.innerHTML = '<div class="card">Session not found.</div>';
    return;
  }
  const calls = turns.filter(t => t.type === 'assistant');
  const totalIn = calls.reduce((sum, t) => sum + (t.input_tokens || 0), 0);
  const totalOut = calls.reduce((sum, t) => sum + (t.output_tokens || 0), 0);
  const totalCacheRd = calls.reduce((sum, t) => sum + (t.cache_read_tokens || 0), 0);
  const totalCacheWrite = calls.reduce((sum, t) => sum + (t.cache_write_tokens || 0), 0);
  const totalReasoning = calls.reduce((sum, t) => sum + (t.reasoning_output_tokens || 0), 0);
  const total = calls.reduce((sum, t) => sum + totalTokens(t), 0);
  const toolCount = calls.reduce((sum, t) => sum + eventsFor(t).filter(e => e.kind === 'tool').length, 0);
  const compactCount = calls.reduce((sum, t) => sum + eventsFor(t).filter(e => e.kind === 'compaction').length, 0);
  const source = turns[0].source || 'claude';
  const timeline = buildPromptTimeline(turns);
  const slug = turns[0].project_slug || '';
  const cwd = (turns.find(t => t.cwd) || {}).cwd || '';
  const base = cwd ? cwd.replace(/\\/g, '/').replace(/\/+$/, '').split('/').pop() : '';
  const project = base || slug;
  const started = turns[0].timestamp || '';
  const ended = turns[turns.length - 1].timestamp || '';
  const firstPrompt = (turns.find(t => t.type === 'user' && t.prompt_text) || {}).prompt_text;
  const promptTitle = firstPrompt ? promptPreview(firstPrompt, 120) : null;
  const title = turns[0].session_title
    || (promptTitle === 'Prompt unavailable' ? null : promptTitle)
    || `Session ${shortSessionId(id)}`;

  root.innerHTML = `
    <div class="card">
      <h2 style="display:flex;align-items:center">
        <span class="blur-sensitive">${safe(fmt.short(title, 120))}</span>
        <span class="spacer"></span>
        <a href="#/sessions" class="muted">← all sessions</a>
      </h2>
      <div class="flex muted session-overview">
        <span class="blur-sensitive">${safe(project)}</span>
        <span class="badge">${safe(source)}</span>
        <span>${fmt.ts(started)} → ${fmt.ts(ended)}</span>
        <span>${fmt.int(timeline.promptCount)} turns · ${fmt.int(calls.length)} calls · ${fmt.int(toolCount)} tools${compactCount ? ` · ${fmt.int(compactCount)} compactions` : ''}</span>
        <span title="${fmt.int(total)} total tokens">${millionTokens(total)} total · ${millionTokens(totalIn)} fresh in · ${millionTokens(totalOut)} out · ${millionTokens(totalCacheRd)} cache rd${totalCacheWrite ? ` · ${millionTokens(totalCacheWrite)} cache write` : ''} · ${millionTokens(totalReasoning)} reasoning</span>
      </div>
      ${source === 'codex' && turns[0].source_file ? `<details class="session-source"><summary>JSONL source</summary><code class="blur-sensitive">${safe(turns[0].source_file)}</code></details>` : ''}
    </div>

    <div class="card" style="margin-top:16px">
      <h3>Prompt timeline</h3>
      <div class="session-turn-list">
        ${timeline.entries.map(entry => renderTurn(entry, timeline.callNumbers)).join('')}
        ${timeline.unassigned.detailRows.length ? renderTurn(timeline.unassigned, timeline.callNumbers) : ''}
      </div>
    </div>`;
}
