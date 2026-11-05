"""Single-page web UI served by jobsearcher.web.

The __HEADLINE__ and __PROFILE_SUMMARY__ placeholders are replaced with
[profile] values at serve time. Trackers are client-side only, in
localStorage under `appliedJobs` / `offRoleJobs` keyed by
Direct_Apply_URL — keys unchanged from the old checkbox UI, so existing
marks survive.

Theming: ivory/sage/emerald/forest/gold estate palette; the toolbar
◐/☾/☀ button cycles auto (follows the OS via prefers-color-scheme) >
dark > light, persisted under localStorage themeMode; html.dark /
html.light classes force a palette, the duplicated palette blocks must
stay in sync (checked by looking at them together).

Insights column: one AI pill per annotated row; clicking expands an
insdetail panel with salary/YOE tags, stack and the full note. The
column header sorts annotated-first; the toolbar has an AI-tag filter
(#aif: annotated / remote-global / remote-region / salary).
"""

WEB_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Live Openings Feed</title>
<style>
  /* Palette: Ivory #F2EBDD · Sage #78947F · Emerald #185844 ·
     Forest #102F27 · Antique Gold #B08A4F (plus a muted wine for ✕ marks) */
  :root {
    color-scheme: light;
    --bg: #f2ebdd; --fg: #102f27; --fg-soft: #3c544a; --sm: #5a6f61;
    --muted: #67796c; --faint: #8fa094;
    --surface: #f8f3e7; --surface-2: #efe8d8; --soft: #e6dfcb;
    --border: #d9d0bd; --border-soft: #e4dccb; --input-border: #c8bea5;
    --accent: #185844; --btn-bg: #185844; --btn-hover: #124434; --btn-fg: #f2ebdd; --ring: rgba(24,88,68,.18);
    --ok: #185844; --ok-strong: #1d6a4f; --ok-soft: #e3ecdf; --ok-border: #78947f; --ok-deep: #14523c;
    --bad: #9c3f34; --bad-strong: #a34a3e; --bad-soft: #f1e2dc; --bad-border: #d3a79b; --bad-tint: #f2e3dd;
    --row-hover: #f7f1e3; --toolbar-bg: rgba(242,235,221,.92);
    --seg-on-bg: #102f27; --seg-on-fg: #f2ebdd;
    --ats-bg: #185844; --ats-fg: #f2ebdd;
    --yoe-soft: #f1e8cf; --yoe-border: #b08a4f; --yoe-fg: #7c5f1f;
    --mark-bg: #f3dfae; --mark-fg: #102f27;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: var(--fg); }
  .wrap { max-width: 1240px; margin: 0 auto; padding: 20px 24px 64px; }
  header h1 { margin: 0; font-size: 20px; display: flex; align-items: center; gap: 10px; }
  /* Dark theme = Forest base, Ivory text, Sage/gold accents. Active via the
     toolbar toggle (html.dark) OR automatically when the OS is dark (the
     prefers-color-scheme block at the end); html.light pins light even on a
     dark OS. Toggle states: auto (default) > dark > light, remembered in
     localStorage under themeMode. */
  html.dark {
    color-scheme: dark;
    --bg: #102f27; --fg: #f2ebdd; --fg-soft: #cfd9cc; --sm: #a9b8ab;
    --muted: #93a598; --faint: #6e8177;
    --surface: #16362c; --surface-2: #1b4236; --soft: #1f4a3c;
    --border: #2b5546; --border-soft: #23493c; --input-border: #3a6354;
    --accent: #d3b273; --btn-bg: #d3b273; --btn-hover: #c2a262; --btn-fg: #102f27; --ring: rgba(211,178,115,.25);
    --ok: #8fc79d; --ok-strong: #2e8b62; --ok-soft: #1c4034; --ok-border: #3e6b53; --ok-deep: #7fbf9a;
    --bad: #d98a80; --bad-strong: #a34a3e; --bad-soft: #3a2523; --bad-border: #6e443f; --bad-tint: #33201e;
    --row-hover: #16382d; --toolbar-bg: rgba(16,47,39,.9);
    --seg-on-bg: #f2ebdd; --seg-on-fg: #102f27;
    --ats-bg: #78947f; --ats-fg: #102f27;
    --yoe-soft: #312c18; --yoe-border: #b08a4f; --yoe-fg: #d8b877;
    --mark-bg: #d3b273; --mark-fg: #102f27;
  }
  html.light {
    color-scheme: light;
    --bg: #f2ebdd; --fg: #102f27; --fg-soft: #3c544a; --sm: #5a6f61;
    --muted: #67796c; --faint: #8fa094;
    --surface: #f8f3e7; --surface-2: #efe8d8; --soft: #e6dfcb;
    --border: #d9d0bd; --border-soft: #e4dccb; --input-border: #c8bea5;
    --accent: #185844; --btn-bg: #185844; --btn-hover: #124434; --btn-fg: #f2ebdd; --ring: rgba(24,88,68,.18);
    --ok: #185844; --ok-strong: #1d6a4f; --ok-soft: #e3ecdf; --ok-border: #78947f; --ok-deep: #14523c;
    --bad: #9c3f34; --bad-strong: #a34a3e; --bad-soft: #f1e2dc; --bad-border: #d3a79b; --bad-tint: #f2e3dd;
    --row-hover: #f7f1e3; --toolbar-bg: rgba(242,235,221,.92);
    --seg-on-bg: #102f27; --seg-on-fg: #f2ebdd;
    --ats-bg: #185844; --ats-fg: #f2ebdd;
    --yoe-soft: #f1e8cf; --yoe-border: #b08a4f; --yoe-fg: #7c5f1f;
    --mark-bg: #f3dfae; --mark-fg: #102f27;
  }
  .logo { width: 30px; height: 30px; border-radius: 8px; flex: none;
          background: linear-gradient(135deg, #185844, #b08a4f); color: #f2ebdd;
          display: inline-flex; align-items: center; justify-content: center; font-size: 15px; }
  .sub { color: var(--muted); margin-top: 2px; font-size: 13px; }
  .toolbar { position: sticky; top: 0; z-index: 10; display: flex; gap: 10px; align-items: center;
             flex-wrap: wrap; background: var(--toolbar-bg); backdrop-filter: blur(6px);
             padding: 12px 0 10px; border-bottom: 1px solid var(--border); margin-top: 16px; }
  .search { position: relative; flex: 1 1 260px; }
  .search input { width: 100%; padding: 8px 32px 8px 34px; border: 1px solid var(--input-border);
                  border-radius: 8px; font-size: 14px; background: var(--surface); color: var(--fg); }
  .search input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--ring); }
  .search .icon { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--faint); }
  .search .clear { position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
                   border: 0; background: none; cursor: pointer; color: var(--faint); font-size: 15px;
                   padding: 2px 7px; border-radius: 6px; display: none; }
  .search .clear:hover { color: var(--fg); background: var(--border-soft); }
  .search.hasq .clear { display: block; }
  select { padding: 8px 10px; border: 1px solid var(--input-border); border-radius: 8px; font-size: 13px;
           background: var(--surface); color: var(--fg); cursor: pointer; max-width: 170px; }
  .seg { display: inline-flex; align-items: stretch; border: 1px solid var(--input-border); border-radius: 999px;
         overflow: hidden; background: var(--surface); flex: none; }
  .segbtn { padding: 8px 13px; border: 0; border-right: 1px solid var(--border); background: transparent;
            cursor: pointer; font-size: 13px; color: var(--fg-soft); white-space: nowrap; }
  .segbtn:last-child { border-right: 0; }
  .segbtn:hover { background: var(--soft); }
  .segbtn.on { background: var(--seg-on-bg); color: var(--seg-on-fg); }
  .segbtn b { font-weight: 600; }
  .btn { padding: 8px 14px; border: 0; border-radius: 8px; background: var(--btn-bg); color: var(--btn-fg);
         font-size: 13px; font-weight: 500; cursor: pointer; }
  .btn:hover { background: var(--btn-hover); }
  .btn:disabled { opacity: .55; cursor: wait; }
  .tbtn { padding: 0; width: 34px; height: 34px; flex: none; border: 1px solid var(--input-border);
          border-radius: 8px; background: var(--surface); color: var(--muted); font-size: 15px;
          cursor: pointer; line-height: 1; }
  .tbtn:hover { background: var(--soft); color: var(--fg); }
  .statline { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 6px; align-items: center; }
  .chip { border: 1px solid var(--border); border-radius: 999px; padding: 4px 12px; background: var(--surface);
          font-size: 12.5px; color: var(--sm); }
  .chip b { color: var(--fg); font-weight: 600; }
  .chip.green b { color: var(--ok); }
  .chip.red b { color: var(--bad); }
  .chip.plain { cursor: default; }
  #status { color: var(--muted); font-size: 12.5px; margin-left: auto; }
  details.tracker { margin: 12px 0; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
  details.tracker summary { cursor: pointer; padding: 11px 16px; font-weight: 600; font-size: 13.5px;
                            list-style: none; display: flex; align-items: center; gap: 8px;
                            border-radius: 12px; }
  details.tracker summary::-webkit-details-marker { display: none; }
  details.tracker summary:hover { background: var(--surface-2); }
  .sign::before { content: "▸"; color: var(--faint); display: inline-block; width: 14px; }
  details[open] .sign::before { content: "▾"; }
  .trkbody { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding: 2px 16px 14px; }
  @media (max-width: 860px) { .trkbody { grid-template-columns: 1fr; } }
  .trk h4 { margin: 0 0 6px; font-size: 11.5px; text-transform: uppercase; letter-spacing: .05em;
            color: var(--muted); }
  .trk ul { list-style: none; margin: 0; padding: 0; max-height: 250px; overflow: auto; }
  .trk li { display: flex; align-items: baseline; gap: 8px; padding: 6px 8px;
            border-bottom: 1px solid var(--soft); font-size: 13px; }
  .trk li a { color: inherit; text-decoration: none; flex: 1; }
  .trk li a:hover { color: var(--accent); }
  .trk li .d { color: var(--faint); font-size: 11.5px; white-space: nowrap; }
  .trk .x { border: 0; background: none; color: var(--faint); cursor: pointer; font-size: 13px;
            padding: 0 2px; flex: none; }
  .trk .x:hover { color: var(--bad-strong); }
  .emptynote { color: var(--faint); font-size: 12.5px; font-style: italic; display: block; padding: 4px 0; }
  .trkActions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; grid-column: 1 / -1; }
  .mini { font-size: 12px; padding: 5px 11px; border-radius: 7px; border: 1px solid var(--input-border);
          background: var(--surface); color: var(--fg-soft); cursor: pointer; }
  .mini:hover { border-color: var(--faint); }
  .mini.danger { color: var(--bad); border-color: var(--bad-border); }
  .mini.danger:hover { background: var(--bad-soft); }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: auto; margin-top: 12px; }
  table { border-collapse: collapse; width: 100%; font-size: 13.5px; min-width: 880px; }
  thead th { position: sticky; top: 0; background: var(--surface-2); z-index: 5; text-align: left; padding: 10px 14px;
             font-size: 11.5px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted);
             border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; white-space: nowrap; }
  thead th.nosort { cursor: default; }
  thead th:hover:not(.nosort) { color: var(--fg); }
  thead th.asc::after { content: " ↑"; color: var(--accent); }
  thead th.desc::after { content: " ↓"; color: var(--accent); }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border-soft); vertical-align: top; }
  tbody tr:hover { background: var(--row-hover); }
  tr.status-applied { background: var(--ok-soft); }
  tr.status-applied td:first-child { box-shadow: inset 3px 0 0 var(--ok-strong); }
  tr.status-hidden { background: var(--bad-tint); }
  tr.status-hidden td:first-child { box-shadow: inset 3px 0 0 var(--bad-strong); }
  td.act { white-space: nowrap; width: 1%; }
  .pill { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px;
          font-size: 13px; padding: 0; border-radius: 999px; cursor: pointer;
          border: 1px solid var(--input-border); background: var(--surface); color: var(--fg-soft); }
  .pill.ok { color: var(--ok); border-color: var(--ok-border); margin-right: 6px; }
  .pill.ok:hover { background: var(--ok-soft); }
  .pill.no { color: var(--bad); border-color: var(--bad-border); }
  .pill.no:hover { background: var(--bad-soft); }
  .pill.on.ok { background: var(--ok-strong); border-color: var(--ok-strong); color: #fff; }
  .pill.on.no { background: var(--bad-strong); border-color: var(--bad-strong); color: #fff; }
  .ats { display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .05em;
         padding: 2px 7px; border-radius: 999px; background: var(--ats-bg); color: var(--ats-fg);
         margin-right: 7px; vertical-align: 1px; white-space: nowrap; }
  .co { font-weight: 600; }
  .stamp { font-size: 11px; color: var(--ok); margin-top: 1px; }
  .go { color: var(--accent); text-decoration: none; font-weight: 500; white-space: nowrap; }
  .go:hover { text-decoration: underline; }
  .yoe { white-space: nowrap; }
  .yoe .known { background: var(--yoe-soft); color: var(--yoe-fg); border-radius: 6px; padding: 1px 8px;
                font-size: 12px; font-weight: 600; }
  .yoe .na { color: var(--faint); font-size: 12px; }
  /* AI Insights: one quiet pill per row (colored by remote match); click
     expands the full annotation — salary/YOE tags, stack, whole note. */
  .ins { max-width: 300px; font-size: 11.5px; color: var(--sm); }
  .aipill { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--ok-border);
            border-radius: 999px; padding: 2px 9px; background: var(--ok-soft); color: var(--ok);
            font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; }
  .aipill.rem-r { border-color: var(--bad-border); background: var(--bad-soft); color: var(--bad); }
  .aipill .c { font-weight: 400; opacity: .8; }
  .insdetail { margin-top: 5px; padding: 7px 9px; border: 1px solid var(--border);
               border-radius: 8px; background: var(--surface-2); font-size: 11px;
               color: var(--sm); line-height: 1.5; }
  .insdetail .tag { display: inline-block; border: 1px solid var(--border); border-radius: 999px;
                    padding: 1px 8px; margin: 1px 3px 1px 0; background: var(--surface); font-size: 10.5px;
                    color: var(--fg-soft); white-space: nowrap; }
  .insdetail .tag.yoe { border-color: var(--yoe-border); background: var(--yoe-soft); color: var(--yoe-fg); }
  .insdetail .stk { margin: 4px 0 0; font-size: 10.5px; color: var(--fg); font-weight: 600; }
  .insdetail .note { margin: 3px 0 0; color: var(--sm); }
  .ins .na { color: var(--faint); font-size: 12px; }
  mark { background: var(--mark-bg); color: var(--mark-fg); border-radius: 2px; padding: 0 1px; }
  #empty { display: none; text-align: center; color: var(--faint); padding: 34px 10px; font-size: 13.5px; }
  .hidden { display: none !important; }
  @media (max-width: 640px) { .wrap { padding: 14px 12px 48px; } #status { width: 100%; margin: 6px 0 0; } }
  /* Auto.Dark: follows the OS appearance (System Settings → Appearance);
     html.dark above forces it via the toggle, html.light pins light. */
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --bg: #102f27; --fg: #f2ebdd; --fg-soft: #cfd9cc; --sm: #a9b8ab;
      --muted: #93a598; --faint: #6e8177;
      --surface: #16362c; --surface-2: #1b4236; --soft: #1f4a3c;
      --border: #2b5546; --border-soft: #23493c; --input-border: #3a6354;
      --accent: #d3b273; --btn-bg: #d3b273; --btn-hover: #c2a262; --btn-fg: #102f27; --ring: rgba(211,178,115,.25);
      --ok: #8fc79d; --ok-strong: #2e8b62; --ok-soft: #1c4034; --ok-border: #3e6b53; --ok-deep: #7fbf9a;
      --bad: #d98a80; --bad-strong: #a34a3e; --bad-soft: #3a2523; --bad-border: #6e443f; --bad-tint: #33201e;
      --row-hover: #16382d; --toolbar-bg: rgba(16,47,39,.9);
      --seg-on-bg: #f2ebdd; --seg-on-fg: #102f27;
      --ats-bg: #78947f; --ats-fg: #102f27;
      --yoe-soft: #312c18; --yoe-border: #b08a4f; --yoe-fg: #d8b877;
      --mark-bg: #d3b273; --mark-fg: #102f27;
    }
  }
</style>
<script>
  // Apply the remembered theme before first paint (no flash). 'auto' (the
  // default) sets no class: the OS color-scheme media query decides.
  try { var _m = localStorage.getItem('themeMode');
        if (_m === 'dark') document.documentElement.className = 'dark';
        else if (_m === 'light') document.documentElement.className = 'light'; } catch (e) {}
</script>
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
    <select id="aif" onchange="render()" title="Filter by AI annotation">
      <option value="all">Insights: all</option>
      <option value="has">AI annotated only</option>
      <option value="remote-global">AI: remote-global</option>
      <option value="remote-region">AI: remote-region</option>
      <option value="salary">AI: salary listed</option>
    </select>
    <div class="seg" id="viewSeg" role="group" aria-label="Category view">
      <button class="segbtn" data-view="active">Active <b id="cntAct">0</b></button>
      <button class="segbtn" data-view="applied">✓ Applied <b id="cntApp">0</b></button>
      <button class="segbtn" data-view="off">✕ Not for me <b id="cntOff">0</b></button>
      <button class="segbtn" data-view="all">All <b id="cntAll">0</b></button>
    </div>
    <button class="btn" id="go" onclick="refresh(true)" title="Force a full re-scrape now (~1 min); results swap in automatically when done">Refresh jobs</button>
    <button class="tbtn" id="modeBtn" onclick="cycleTheme()" title="Theme"></button>
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
          <th onclick="sortBy('AIInsights')" title="AI annotation (Gemini Flash-Lite); click to sort — annotated roles first. Click a row's pill for the full note">Insights</th>
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

// Theme toggle: 'auto' (default, follows the OS appearance), 'dark', 'light' —
// cycled with the toolbar button, remembered under themeMode. The CSS maps
// html.dark / html.light to forced palettes and the prefers-color-scheme
// block handles auto.
let THEME = 'auto';
try { const t = localStorage.getItem('themeMode');
      if (t === 'dark' || t === 'light') THEME = t; } catch (e) {}
function applyTheme() {
  document.documentElement.classList.toggle('dark', THEME === 'dark');
  document.documentElement.classList.toggle('light', THEME === 'light');
  const b = $('#modeBtn');
  if (b) {
    b.textContent = THEME === 'dark' ? '☾' : (THEME === 'light' ? '☀' : '◐');
    b.title = 'Theme: ' + (THEME === 'auto' ? 'system default' : THEME) + ' — click to switch';
  }
  try { localStorage.setItem('themeMode', THEME); } catch (e) {}
}
function cycleTheme() {
  THEME = THEME === 'auto' ? 'dark' : (THEME === 'dark' ? 'light' : 'auto');
  applyTheme();
}

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

function hasInsights(j) {
  return !!((j.AI_Remote && j.AI_Remote !== 'n/a') || j.AI_Salary
    || (j.AI_YOE && j.AI_YOE !== 'n/a') || j.AI_Stack || j.AI_Note);
}

function cmp(a, b) {
  if (SORT === 'YOE') {
    const x = parseInt(a.Max_Stated_YOE, 10), y = parseInt(b.Max_Stated_YOE, 10);
    const nx = isNaN(x) ? 999 : x, ny = isNaN(y) ? 999 : y;   // n/a sorts last
    return nx - ny;
  }
  if (SORT === 'AIInsights') {
    // Annotated roles first ascending; the ↓ arrow flips it.
    return (hasInsights(b) ? 1 : 0) - (hasInsights(a) ? 1 : 0);
  }
  return String(a[SORT] ?? '').localeCompare(String(b[SORT] ?? ''), undefined,
    { sensitivity: 'base', numeric: true });
}

function render() {
  const q = $('#filter').value.trim().toLowerCase();
  $('#searchbox').classList.toggle('hasq', !!q);
  const ats = $('#ats').value;
  const aif = $('#aif').value;
  const tbody = $('#rows');
  tbody.innerHTML = '';
  const idx = [...JOBS.keys()];
  if (SORT) { idx.sort((x, y) => cmp(JOBS[x], JOBS[y])); if (DESC) idx.reverse(); }
  let shown = 0;
  const frag = document.createDocumentFragment();
  for (const i of idx) {
    const j = JOBS[i], url = keyOf(j);
    if (q) {
      const hay = (j.Company + ' ' + j.Title + ' ' + j.Location + ' ' + j.ATS + ' '
        + (j.AI_Stack || '') + ' ' + (j.AI_Salary || '') + ' ' + (j.AI_Remote || '')
        + ' ' + (j.AI_Note || '')).toLowerCase();
      if (!hay.includes(q)) continue;
    }
    if (ats !== 'all' && j.ATS !== ats) continue;
    if (aif !== 'all') {
      if (aif === 'has') { if (!hasInsights(j)) continue; }
      else if (aif === 'salary') { if (!j.AI_Salary) continue; }
      else if (j.AI_Remote !== aif) continue;   // remote-global / remote-region
    }
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
  const gc = String(j.AI_Remote || '');
  const remCls = gc === 'remote-global' ? ' rem-g' : (gc === 'remote-region' ? ' rem-r' : '');
  const remTag = gc ? `<span class="tag${remCls}">${esc(gc)}</span>` : '';
  const salTag = j.AI_Salary ? `<span class="tag">${esc(j.AI_Salary)}</span>` : '';
  const yoeTag = j.AI_YOE && j.AI_YOE !== 'n/a' ? `<span class="tag yoe">${esc(j.AI_YOE)}</span>` : '';
  const stkLine = j.AI_Stack ? `<div class="stk">${esc(j.AI_Stack)}</div>` : '';
  const noteLine = j.AI_Note ? `<div class="note">${esc(j.AI_Note)}</div>` : '';
  const annotated = hasInsights(j);
  // Collapsed cell = one pill; the detail panel holds everything else. If
  // the model annotated ONLY the remote field, repeat it in the detail so
  // expanding isn't empty.
  let detail = salTag + yoeTag + stkLine + noteLine;
  if (!detail) detail = remTag;
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
    `<td class="ins">` +
    (annotated
      ? `<button type="button" class="aipill${remCls}" title="Show/hide the full AI annotation">` +
        `✦ ${gc ? esc(gc) : 'AI'} <span class="c">▾</span></button>` +
        `<div class="insdetail hidden">${detail}</div>`
      : '<span class="na">n/a</span>') +
    `</td>` +
    `<td>${esc(j.ATS)}</td>` +
    `<td class="act"><a class="go" href="${esc(url)}" target="_blank" rel="noopener">Apply ↗</a></td>`;
  const [pA, pO] = tr.querySelectorAll('.pill');
  pA.onclick = () => toggleApply(url);
  pO.onclick = () => toggleOff(url);
  const pill = tr.querySelector('.aipill');
  if (pill) pill.onclick = () => {
    const d = tr.querySelector('.insdetail');
    const opening = d.classList.contains('hidden');
    d.classList.toggle('hidden');
    pill.querySelector('.c').textContent = opening ? '▴' : '▾';
  };
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
  applyTheme();

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
