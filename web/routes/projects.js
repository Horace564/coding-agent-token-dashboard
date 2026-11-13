import { api, fmt } from '/web/app.js';

export default async function (root) {
  const rows = await api('/api/projects');
  root.innerHTML = `
    <div class="card">
      <h2>Projects</h2>
      <p class="muted" style="margin:-8px 0 14px">Sorted by fresh input, output and cache writes. Choose a source in the top bar.</p>
      <table>
        <thead><tr><th>project</th><th>source</th><th class="num">sessions</th><th class="num">turns</th><th class="num">work tokens</th><th class="num">cache reads</th></tr></thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td title="${fmt.htmlSafe(r.project_slug)}">${fmt.htmlSafe(r.project_name || r.project_slug)}</td>
              <td><span class="badge">${fmt.htmlSafe(r.source)}</span></td>
              <td class="num">${fmt.int(r.sessions)}</td>
              <td class="num">${fmt.int(r.turns)}</td>
              <td class="num">${fmt.int(r.billable_tokens)}</td>
              <td class="num">${fmt.int(r.cache_read_tokens)}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}
