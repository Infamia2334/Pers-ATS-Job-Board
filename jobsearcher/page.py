"""Single-page web UI served by jobsearcher.web.

The __HEADLINE__ and __PROFILE_SUMMARY__ placeholders are replaced with
[profile] values at serve time. Trackers are client-side only, in
localStorage under `appliedJobs` / `offRoleJobs` keyed by
Direct_Apply_URL — keys unchanged from the old checkbox UI, so existing
marks survive.
"""

WEB_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live Openings Feed</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f6f8fa; color: #0f172a; }
  .wrap { max-width: 1240px; margin: 0 auto; padding: 20px 24px 64px; }
  header h1 { margin: 0; font-size: 20px; display: flex; align-items: center; gap: 10px; }
  .logo { width: 30px; height: 30px; border-radius: 8px; flex: none;
          background: linear-gradient(135deg, #2563eb, #7c3aed); color: #fff;
          display: inline-flex; align-items: center; justify-content: center; font-size: 15px; }
  .sub { color: #64748b; margin-top: 2px; font-size: 13px; }
  .toolbar { position: sticky; top: 0; z-index: 10; display: flex; gap: 10px; align-items: center;
             flex-wrap: wrap; background: rgba(246,248,250,.92); backdrop-filter: blur(6px);
             padding: 12px 0 10px; border-bottom: 1px solid #e2e8f0; margin-top: 16px; }
  .search { position: relative; flex: 1 1 260px; }
  .search input { width: 100%; padding: 8px 32px 8px 34px; border: 1px solid #cbd5e1;
                  border-radius: 8px; font-size: 14px; background: #fff; color: #0f172a; }
  .search input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px #2563eb22; }
  .search .icon { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: #94a3b8; }
  .search .clear { position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
                   border: 0; background: none; cursor: pointer; color: #94a3b8; font-size: 15px;
                   padding: 2px 7px; border-radius: 6px; display: none; }
  .search .clear:hover { color: #0f172a; background: #eef2f7; }
  .search.hasq .clear { display: block; }
  select { padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px;
           background: #fff; color: #0f172a; cursor: pointer; max-width: 170px; }
  .seg { display: inline-flex; align-items: stretch; border: 1px solid #cbd5e1; border-radius: 999px;
         overflow: hidden; background: #fff; flex: none; }
  .segbtn { padding: 8px 13px; border: 0; border-right: 1px solid #e2e8f0; background: transparent;
            cursor: pointer; font-size: 13px; color: #334155; white-space: nowrap; }
  .segbtn:last-child { border-right: 0; }
  .segbtn:hover { background: #f1f5f9; }
  .segbtn.on { background: #0f172a; color: #fff; }
  .segbtn b { font-weight: 600; }
  .btn { padding: 8px 14px; border: 0; border-radius: 8px; background: #2563eb; color: #fff;
         font-size: 13px; font-weight: 500; cursor: pointer; }
  .btn:hover { background: #1d4ed8; }
  .btn:disabled { opacity: .55; cursor: wait; }
  .statline { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 6px; align-items: center; }
  .chip { border: 1px solid #e2e8f0; border-radius: 999px; padding: 4px 12px; background: #fff;
          font-size: 12.5px; color: #475569; }
  .chip b { color: #0f172a; font-weight: 600; }
  .chip.green b { color: #15803d; }
  .chip.red b { color: #b91c1c; }
  .chip.plain { cursor: default; }
  #status { color: #64748b; font-size: 12.5px; margin-left: auto; }
  details.tracker { margin: 12px 0; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
  details.tracker summary { cursor: pointer; padding: 11px 16px; font-weight: 600; font-size: 13.5px;
                            list-style: none; display: flex; align-items: center; gap: 8px;
                            border-radius: 12px; }
  details.tracker summary::-webkit-details-marker { display: none; }
  details.tracker summary:hover { background: #f8fafc; }
  .sign::before { content: "▸"; color: #94a3b8; display: inline-block; width: 14px; }
  details[open] .sign::before { content: "▾"; }
  .trkbody { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding: 2px 16px 14px; }
  @media (max-width: 860px) { .trkbody { grid-template-columns: 1fr; } }
  .trk h4 { margin: 0 0 6px; font-size: 11.5px; text-transform: uppercase; letter-spacing: .05em;
            color: #64748b; }
  .trk ul { list-style: none; margin: 0; padding: 0; max-height: 250px; overflow: auto; }
  .trk li { display: flex; align-items: baseline; gap: 8px; padding: 6px 8px;
            border-bottom: 1px solid #f1f5f9; font-size: 13px; }
  .trk li a { color: inherit; text-decoration: none; flex: 1; }
  .trk li a:hover { color: #2563eb; }
  .trk li .d { color: #94a3b8; font-size: 11.5px; white-space: nowrap; }
  .trk .x { border: 0; background: none; color: #94a3b8; cursor: pointer; font-size: 13px;
            padding: 0 2px; flex: none; }
  .trk .x:hover { color: #dc2626; }
  .emptynote { color: #94a3b8; font-size: 12.5px; font-style: italic; display: block; padding: 4px 0; }
  .trkActions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; grid-column: 1 / -1; }
  .mini { font-size: 12px; padding: 5px 11px; border-radius: 7px; border: 1px solid #cbd5e1;
          background: #fff; color: #334155; cursor: pointer; }
  .mini:hover { border-color: #94a3b8; }
  .mini.danger { color: #b91c1c; border-color: #fecaca; }
  .mini.danger:hover { background: #fef2f2; }
  .card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: auto; margin-top: 12px; }
  table { border-collapse: collapse; width: 100%; font-size: 13.5px; min-width: 880px; }
  thead th { position: sticky; top: 0; background: #f8fafc; z-index: 5; text-align: left; padding: 10px 14px;
             font-size: 11.5px; letter-spacing: .04em; text-transform: uppercase; color: #64748b;
             border-bottom: 1px solid #e2e8f0; cursor: pointer; user-select: none; white-space: nowrap; }
  thead th.nosort { cursor: default; }
  thead th:hover:not(.nosort) { color: #0f172a; }
  thead th.asc::after { content: " ↑"; color: #2563eb; }
  thead th.desc::after { content: " ↓"; color: #2563eb; }
  td { padding: 9px 14px; border-bottom: 1px solid #eef2f7; vertical-align: top; }
  tbody tr:hover { background: #f8faff; }
  tr.status-applied { background: #f0fdf4; }
  tr.status-applied td:first-child { box-shadow: inset 3px 0 0 #16a34a; }
  tr.status-hidden { background: #fef6f6; }
  tr.status-hidden td:first-child { box-shadow: inset 3px 0 0 #dc2626; }
  td.act { white-space: nowrap; width: 1%; }
  .pill { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px;
          font-size: 13px; padding: 0; border-radius: 999px; cursor: pointer;
          border: 1px solid #cbd5e1; background: #fff; color: #334155; }
  .pill.ok { color: #15803d; border-color: #86efac; margin-right: 6px; }
  .pill.ok:hover { background: #f0fdf4; }
  .pill.no { color: #b91c1c; border-color: #fecaca; }
  .pill.no:hover { background: #fef2f2; }
  .pill.on.ok { background: #16a34a; border-color: #16a34a; color: #fff; }
  .pill.on.no { background: #dc2626; border-color: #dc2626; color: #fff; }
  .ats { display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .05em;
         padding: 2px 7px; border-radius: 999px; background: #e0e7ff; color: #4338ca;
         margin-right: 7px; vertical-align: 1px; white-space: nowrap; }
  .co { font-weight: 600; }
  .stamp { font-size: 11px; color: #15803d; margin-top: 1px; }
  .go { color: #2563eb; text-decoration: none; font-weight: 500; white-space: nowrap; }
  .go:hover { text-decoration: underline; }
  .yoe { white-space: nowrap; }
  .yoe .known { background: #ecfdf5; color: #047857; border-radius: 6px; padding: 1px 8px;
                font-size: 12px; font-weight: 600; }
  .yoe .na { color: #94a3b8; font-size: 12px; }
  mark { background: #fef08a; border-radius: 2px; padding: 0 1px; }
  #empty { display: none; text-align: center; color: #94a3b8; padding: 34px 10px; font-size: 13.5px; }
  .hidden { display: none !important; }
  @media (max-width: 640px) { .wrap { padding: 14px 12px 48px; } #status { width: 100%; margin: 6px 0 0; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1><span class="logo">◎</span> Live Openings Feed</h1>
    <p class="sub">__HEADLINE__</p>
  </header>

  <div class="toolbar">
    <div class="search" id="searchbox">
      <span class="icon">⌕</span>
      <input id="filter" type="text" autocomplete="off" spellcheck="false"
             placeholder='Search company, title, location…  (press / to focus)'>
      <button class="clear" id="clearq" title="Clear search">✕</button>
    </div>
    <select id="ats" onchange="render()"><option value="all">All sources</option></select>
    <div class="seg" id="viewSeg" role="group" aria-label="Category view">
      <button class="segbtn" data-view="active">Active <b id="cntAct">0</b></button>
      <button class="segbtn" data-view="applied">✓ Applied <b id="cntApp">0</b></button>
      <button class="segbtn" data-view="off">✕ Not for me <b id="cntOff">0</b></button>
      <button class="segbtn" data-view="all">All <b id="cntAll">0</b></button>
    </div>
    <button class="btn" id="go" onclick="refresh(true)" title="Force a full re-scrape now (~1 min); results swap in automatically when done">Refresh jobs</button>
    <span id="status">Loading…</span>
  </div>

  <div class="statline hidden" id="statline">
    <span class="chip plain" id="chipTotal"></span>
    <span class="chip green" id="chipA" title="Mark with the ✓ pill on any row"></span>
    <span class="chip red" id="chipO" title="Mark with the ✕ pill on any row"></span>
    <span class="chip plain" id="chipShown"></span>
  </div>

  <details class="tracker hidden" id="tracker">
    <summary><span class="sign"></span> Application tracker
      <span class="chip green"><b id="trkA">0</b> applied</span>
      <span class="chip red"><b id="trkO">0</b> not for me</span>
    </summary>
    <div class="trkbody">
      <div class="trk">
        <h4>Applied</h4>
        <ul id="listA"></ul>
      </div>
      <div class="trk">
        <h4>Not for me</h4>
        <ul id="listO"></ul>
      </div>
      <div class="trkActions">
        <button class="mini" id="expA" onclick="exportCsv(applied, 'applications.csv')">⬇ Export applied (CSV)</button>
        <button class="mini" id="expO" onclick="exportCsv(offrole, 'not-for-me.csv')">⬇ Export not-for-me (CSV)</button>
        <button class="mini danger" id="wipe" onclick="wipeTracker()">Clear all marks…</button>
      </div>
    </div>
  </details>

  <div class="card hidden" id="card">
    <table id="tbl">
      <thead>
        <tr>
          <th class="nosort">Status</th>
          <th onclick="sortBy('Company')">Company</th>
          <th onclick="sortBy('Title')">Title</th>
          <th onclick="sortBy('Location')">Location</th>
          <th onclick="sortBy('YOE')">Max YOE</th>
          <th onclick="sortBy('ATS')">Source</th>
          <th class="nosort">Apply</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
    <div id="empty">Nothing here — switch back to Active/All above, clear the search box, or hit Refresh jobs.</div>
  </div>
</div>

<script>
'use strict';
const $ = s => document.querySelector(s);
const LS = {
  get(k) { try { return JSON.parse(localStorage.getItem(k) || '{}'); } catch (e) { return {}; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
};
// Storage keys are unchanged from the old tracker — existing marks survive the upgrade.
let applied = LS.get('appliedJobs');
let offrole = LS.get('offRoleJobs');
const saveApplied = () => LS.set('appliedJobs', applied);
const saveOff = () => LS.set('offRoleJobs', offrole);

let JOBS = [], SORT = null, DESC = false;
let renderTimer = null;
// View state: 'active' (default — nothing you've marked), 'applied', 'off'
// or 'all'. Remembered per-browser so Not-for-me stays out of the default
// dashboard after marking jobs.
let VIEW = 'active';
try { const saved = localStorage.getItem('jobsView');
      if (['active', 'applied', 'off', 'all'].includes(saved)) VIEW = saved; } catch (e) {}

function setView(v) {
  VIEW = v;
  try { localStorage.setItem('jobsView', v); } catch (e) {}
  document.querySelectorAll('#viewSeg .segbtn').forEach(b => {
    const on = b.dataset.view === v;
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', on);
  });
  render();
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function rxq(s) { return s.replace(/[.*+?^${}()\\[\\]\\\\]/g, '\\\\$&'); }
function hl(text, q) {
  const e = esc(text);
  if (!q) return e;
  try { return e.replace(new RegExp('(' + rxq(q) + ')', 'ig'), '<mark>$1</mark>'); }
  catch (_) { return e; }
}
function keyOf(j) { return j.Direct_Apply_URL; }
function fmtDate(ts) {
  try { return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }); }
  catch (e) { return ''; }
}

function toggleApply(url) {
  if (applied[url]) delete applied[url]; else applied[url] = Date.now();
  saveApplied(); render(); renderTracker();
}
function toggleOff(url) {
  if (offrole[url]) delete offrole[url]; else offrole[url] = Date.now();
  saveOff(); render(); renderTracker();
}

async function refresh(force) {
  const btn = $('#go'), st = $('#status');
  btn.disabled = true;
  st.textContent = 'Loading cached results…';
  try {
    // Refresh button (force=true) = explicit demand: ?refresh=1 re-scrapes
    // no matter how young the cache is. Page loads call refresh(false):
    // cache-first, the server only kicks a background re-scrape once the
    // config TTL expired — there is never a timer.
    const r = await fetch(force ? '/jobs?refresh=1' : '/jobs', { cache: 'no-store' });
    const data = await r.json();
    JOBS = data.jobs || [];
    buildAtsOptions();
    $('#card').classList.remove('hidden');
    $('#tracker').classList.remove('hidden');
    $('#statline').classList.remove('hidden');
    render(); renderTracker();
    statusLine(data);
    if (data.refreshing) schedulePoll(); else clearPoll();
  } catch (e) {
    st.textContent = 'Failed: ' + e;
  }
  btn.disabled = false;
}

function statusLine(data) {
  const companies = new Set(JOBS.map(j => j.Company)).size;
  const base = JOBS.length
    ? `${JOBS.length} roles · ${companies} companies`
    : 'No matching roles right now';
  $('#status').textContent = data.generated_at
    ? `${base} · scraped ${data.generated_at}` + (data.refreshing ? ' · refreshing in background…' : '')
    : base;
}

// While the server re-scrapes in the background (cache TTL expired), poll
// quietly every 2.5s; when the fresh run lands, swap it in automatically —
// no second click needed.
let pollTimer = null;
function clearPoll() {
  if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
}
function schedulePoll() {
  clearPoll();
  pollTimer = setTimeout(async () => {
    try {
      const data = await (await fetch('/jobs', { cache: 'no-store' })).json();
      if (data.refreshing) { schedulePoll(); return; }
      JOBS = data.jobs || [];
      buildAtsOptions();
      render(); renderTracker();
      statusLine(data);
    } catch (e) {
      schedulePoll();  // network hiccup — stay in polling until it lands
    }
  }, 2500);
}

function buildAtsOptions() {
  const sel = $('#ats'), prev = sel.value;
  const sources = [...new Set(JOBS.map(j => j.ATS))].sort();
  sel.innerHTML = '<option value="all">All sources</option>' +
    sources.map(s => `<option value="${esc(s)}">${esc(s)} (${JOBS.filter(j => j.ATS === s).length})</option>`).join('');
  if (sources.includes(prev)) sel.value = prev;
}

function cmp(a, b) {
  if (SORT === 'YOE') {
    const x = parseInt(a.Max_Stated_YOE, 10), y = parseInt(b.Max_Stated_YOE, 10);
    const nx = isNaN(x) ? 999 : x, ny = isNaN(y) ? 999 : y;   // n/a sorts last
    return nx - ny;
  }
  return String(a[SORT] ?? '').localeCompare(String(b[SORT] ?? ''), undefined,
    { sensitivity: 'base', numeric: true });
}

function render() {
  const q = $('#filter').value.trim().toLowerCase();
  $('#searchbox').classList.toggle('hasq', !!q);
  const ats = $('#ats').value;
  const tbody = $('#rows');
  tbody.innerHTML = '';
  const idx = [...JOBS.keys()];
  if (SORT) { idx.sort((x, y) => cmp(JOBS[x], JOBS[y])); if (DESC) idx.reverse(); }
  let shown = 0;
  const frag = document.createDocumentFragment();
  for (const i of idx) {
    const j = JOBS[i], url = keyOf(j);
    if (q) {
      const hay = (j.Company + ' ' + j.Title + ' ' + j.Location + ' ' + j.ATS).toLowerCase();
      if (!hay.includes(q)) continue;
    }
    if (ats !== 'all' && j.ATS !== ats) continue;
    // Category views: 'active' hides everything already marked, which is
    // the default dashboard behaviour.
    const isA = !!applied[url], isO = !isA && !!offrole[url];
    if (VIEW === 'active' && (isA || isO)) continue;
    if (VIEW === 'applied' && !isA) continue;
    if (VIEW === 'off' && !isO) continue;
    shown++;
    frag.appendChild(rowEl(j, url, q));
  }
  tbody.appendChild(frag);
  updateChips(shown);
  $('#empty').style.display = shown ? 'none' : '';
}

function rowEl(j, url, q) {
  // One innerHTML per row replaces the per-cell element construction —
  // ~15x fewer DOM ops, which is what made 300-row renders take seconds.
  const tr = document.createElement('tr');
  const isA = !!applied[url], isO = !!offrole[url] && !isA;
  if (isA) tr.className = 'status-applied';
  else if (isO) tr.className = 'status-hidden';
  const y = String(j.Max_Stated_YOE);
  tr.innerHTML =
    `<td class="act">` +
    `<button type="button" class="pill ok${isA ? ' on' : ''}" title="${isA ? 'Unmark as applied' : 'Mark as applied'}" aria-label="${isA ? 'Unmark as applied' : 'Mark as applied'}">✓</button>` +
    `<button type="button" class="pill no${isO ? ' on' : ''}" title="${isO ? 'Show again (currently &quot;not for me&quot;)' : 'Not for me — hide row'}" aria-label="${isO ? 'Show again (currently not for me)' : 'Not for me — hide row'}">✕</button>` +
    `</td>` +
    `<td><span class="ats">${esc(j.ATS)}</span><span class="co">${hl(j.Company, q)}</span>` +
    (isA ? `<div class="stamp">applied ${fmtDate(applied[url])}</div>` : '') +
    `</td>` +
    `<td>${hl(j.Title, q)}</td>` +
    `<td>${hl(j.Location, q)}</td>` +
    `<td class="yoe">${y === 'n/a' ? '<span class="na">n/a</span>' : `<span class="known">${esc(y)} yr</span>`}</td>` +
    `<td>${esc(j.ATS)}</td>` +
    `<td class="act"><a class="go" href="${esc(url)}" target="_blank" rel="noopener">Apply ↗</a></td>`;
  const [pA, pO] = tr.querySelectorAll('.pill');
  pA.onclick = () => toggleApply(url);
  pO.onclick = () => toggleOff(url);
  return tr;
}

function counts() {
  let act = 0, a = 0, o = 0;
  for (const j of JOBS) {
    const url = keyOf(j);
    if (applied[url]) a++;
    else if (offrole[url]) o++;
    else act++;
  }
  return { act, a, o };
}

function updateChips(shown) {
  const { act, a, o } = counts();
  $('#chipTotal').innerHTML = `<b>${JOBS.length}</b> scraped`;
  $('#chipA').innerHTML = `<b>${a}</b> applied`;
  $('#chipO').innerHTML = `<b>${o}</b> not for me`;
  $('#chipShown').innerHTML = `${shown} shown`;
  $('#cntAct').textContent = act;
  $('#cntApp').textContent = a;
  $('#cntOff').textContent = o;
  $('#cntAll').textContent = JOBS.length;
}

function renderTracker() {
  const { a, o } = counts();
  $('#trkA').textContent = a;
  $('#trkO').textContent = o;
  fillTrk('#listA', JOBS.filter(j => applied[keyOf(j)]).sort((x, y) => applied[keyOf(y)] - applied[keyOf(x)]), applied);
  fillTrk('#listO', JOBS.filter(j => offrole[keyOf(j)] && !applied[keyOf(j)]).sort((x, y) => offrole[keyOf(y)] - offrole[keyOf(x)]), offrole);
}

function fillTrk(sel, arr, map) {
  const ul = $(sel);
  ul.innerHTML = '';
  if (!arr.length) {
    ul.innerHTML = '<li><span class="emptynote">Nothing here yet — use the ✓ (applied) or ✕ (not for me) pills on a row.</span></li>';
    return;
  }
  for (const j of arr) {
    const url = keyOf(j);
    const li = document.createElement('li');
    li.innerHTML =
      `<a href="${esc(url)}" target="_blank" rel="noopener"><span class="co">${esc(j.Company)}</span> — ${esc(j.Title)}</a>` +
      `<span class="d">${fmtDate(map[url])}</span>`;
    const x = document.createElement('button');
    x.className = 'x'; x.textContent = '✕'; x.title = 'Remove from tracker';
    x.onclick = () => { delete map[url]; (map === applied ? saveApplied() : saveOff()); render(); renderTracker(); };
    li.appendChild(x);
    ul.appendChild(li);
  }
}

function exportCsv(map, fname) {
  const rows = [['Company', 'Title', 'Location', 'Source', 'URL', 'Marked at ISO']]
    .concat(JOBS.filter(j => map[keyOf(j)]).map(j =>
      [j.Company, j.Title, j.Location, j.ATS, keyOf(j), new Date(map[keyOf(j)]).toISOString()]));
  const csv = rows.map(r => r.map(c => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = fname;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(a.href);
}

function wipeTracker() {
  if (!confirm('Clear ALL applied + not-for-me marks? This cannot be undone.')) return;
  if (!confirm('Last chance — really clear both trackers?')) return;
  applied = {}; offrole = {};
  saveApplied(); saveOff();
  setView('active');
  renderTracker();
}

function sortBy(col) {
  DESC = (SORT === col) ? !DESC : false;
  SORT = col;
  document.querySelectorAll('th[data-sortable]') .forEach(() => {});
  document.querySelectorAll('#tbl thead th').forEach(th => th.classList.remove('asc', 'desc'));
  const ths = [...document.querySelectorAll('#tbl thead th')];
  const th = ths.find(t => t.getAttribute('onclick') === `sortBy('${col}')`);
  if (th) th.classList.add(DESC ? 'desc' : 'asc');
  render();
}

document.addEventListener('DOMContentLoaded', () => {
  // Category views are the first-class control now: Active hides everything
  // you've marked; see applied / not-for-me lists in their own views.
  document.querySelectorAll('#viewSeg .segbtn').forEach(b =>
    b.addEventListener('click', () => setView(b.dataset.view)));
  setView(VIEW);

  $('#filter').addEventListener('input', () => {
    // Debounce: a keystroke on a 300-row table rerenders everything, so
    // coalesce bursts instead of rebuilding mid-typing.
    clearTimeout(renderTimer);
    renderTimer = setTimeout(render, 100);
  });
  $('#clearq').addEventListener('click', () => { $('#filter').value = ''; $('#filter').focus(); render(); });
  document.addEventListener('keydown', e => {
    if (e.key === '/' && !/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) {
      e.preventDefault(); $('#filter').focus();
    }
    if (e.key === 'Escape' && document.activeElement === $('#filter')) {
      $('#filter').value = ''; $('#filter').blur(); render();
    }
  });
  refresh(false);  // page load = cache-first; only the button forces a scrape
});
</script>
</body>
</html>
"""
