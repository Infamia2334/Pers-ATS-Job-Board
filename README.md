# Pers-ATS-Job-Board

Personal job-discovery engine: scrapes public job-posting APIs (Ashby,
Greenhouse, Lever) plus six no-auth feeds (YC Work at a Startup, HN
"Who is hiring?", RemoteOK, WeWorkRemotely, LinkedIn guest cards, Zoho
Recruit sites), filters everything through your personal profile, and
serves a clickable application tracker.

Stdlib-only Python — no `requirements.txt`, no install step.

## Usage

```sh
./start.sh          # start the web UI (opens the browser) — ./start.sh stop|status also work
python3 discover_jobs.py            # CSV mode: write Live_Openings_Feed.csv + console preview
python3 discover_jobs.py --verify   # liveness-check every configured board/feed slug
```

The web UI (`start.sh`) is the primary mode: it scrapes in the background on
startup, serves a cached result set instantly, and refreshes silently when
the cache (10 min by default) goes stale.

The code is a package (`jobsearcher/`) split by responsibility — `config.py`
loads the TOML and compiles filter regexes, `fetch.py` is HTTP plumbing,
`sources.py` has one `check_*` per board/feed, `engine.py` runs them
concurrently, `page.py`/`web.py` serve the UI, `cli.py` holds CSV mode and
`--verify`. `discover_jobs.py` at the root is a thin launcher for those modes.

## What it looks for

Everything tunable lives in **`config.toml`** — the single source of truth:

| Section    | Controls                                                                 |
|------------|--------------------------------------------------------------------------|
| `[profile]` | Personal headline, years-of-experience cap, master resume path         |
| `[filters]` | Role/location include+exclude regexes (or plain keyword lists), sort priority tiers |
| `[boards]`  | Per-ATS on/off switches + board slugs; company allow/drop lists         |
| `[feeds]`   | On/off switches and settings for the six non-ATS sources                |
| `[run]`     | Duplicate removal, thread count, timeouts, web port, cache TTL, CSV path |

After changing board slugs, run `--verify`: wrong slugs fail silently
everywhere else.

## Web UI features

- Table of matching roles with source, location, stated max-YOE and a one-click apply link.
- Track applications (✓) and "not for me" (✕) per row — persisted in the browser's
  `localStorage`, surviving restarts; export either list to CSV from the tracker panel.
- Instant search (`/` to focus) with match highlighting, per-source filter, sortable columns.
- Rows are priority-sorted: remote/global first, then the configured location tiers.

Note: the trackers are per-browser only (no server-side storage), and the join
key is the posting's apply URL — if a posting's URL changes between scrapes,
its marks are orphaned.

## Requirements

- **Python 3.12+** (stdlib `tomllib` parses the config — `.python-version`
  pins the pyenv virtualenv where present). Uses ~110 live HTTP endpoints per
  run, so it needs network access.
